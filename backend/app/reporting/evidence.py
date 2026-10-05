"""
Evidence for reports: cleaning photos and videos so they can't give the reporter away, and storing them.

Photos and videos carry hidden details: where they were taken (GPS), the phone's make, model and owner's name, and
the exact time. Any of these could identify the reporter, so nothing is saved until they are removed:

- Photos (JPEG, PNG, WebP) are opened, turned the right way up, and then rebuilt from their pixels alone into a
  new file. Nothing hidden can survive, because nothing but the pixels is copied.
- Videos (MP4, MOV, WebM) are re-packed with ffmpeg, keeping only the picture and (if the reporter wants) the sound.
  All metadata (location, device, owner, dates, chapters) is dropped, and so are extra tracks such as the GPS
  tracks some cameras record. The picture itself isn't re-encoded, so this is quick and loses no quality.

What cleaning can NOT do: remove what can be seen or heard. A face, a reflection, a view from a particular desk or
a voice can still identify someone, and the reporter is warned about this before uploading.
"""
import io
import os
import secrets
import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import EVIDENCE_DIR
from app.reporting.models import Evidence

MAX_FILES = 6                         # per case
MAX_PHOTO_BYTES = 15 * 1024 * 1024    # 15 MB
MAX_VIDEO_BYTES = 100 * 1024 * 1024   # 100 MB, about a minute or two of phone video
Image.MAX_IMAGE_PIXELS = 60_000_000   # refuse "decompression bombs" (tiny files that expand to huge images)
PHOTO_FORMATS = {"JPEG": ("image/jpeg", "jpg"), "PNG": ("image/png", "png"), "WEBP": ("image/webp", "webp")}
VIDEO_FORMATS = {"mp4": ("video/mp4", "mp4"), "webm": ("video/webm", "webm")}


class NotUsable(ValueError):
    """The file isn't a photo or video we can clean; the message says why, in plain words."""


class VideoUnavailable(RuntimeError):
    """This server can't clean videos (ffmpeg is missing), so it won't accept them."""


# ─── Telling files apart (by their contents, never by their name or the browser's word for it) ────────────────
def kind_of(head: bytes) -> str | None:
    """'photo', 'video' or None, from the file's first bytes."""
    if head[:3] == b"\xff\xd8\xff" or head[:8] == b"\x89PNG\r\n\x1a\n" or (head[:4] == b"RIFF" and head[8:12] == b"WEBP"):
        return "photo"
    if head[4:8] == b"ftyp" or head[:4] == b"\x1a\x45\xdf\xa3":  # MP4/MOV, or WebM
        return "video"
    return None


# ─── Photos ───────────────────────────────────────────────────────────────────
def clean_photo(data: bytes) -> tuple[bytes, str, str]:
    """The photo rebuilt from its pixels only: (bytes, content type, extension)."""
    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()  # checks the file isn't broken or disguised
            fmt = probe.format
        if fmt not in PHOTO_FORMATS:
            raise NotUsable("Photos must be JPEG, PNG or WebP.")
        with Image.open(io.BytesIO(data)) as img:
            img.seek(0)                        # an animated image keeps only its first frame
            img = ImageOps.exif_transpose(img)  # keep it the right way up before the orientation tag is dropped
            alpha = "A" in img.getbands() or "transparency" in img.info
            mode = "RGB" if fmt == "JPEG" else ("RGBA" if alpha else "RGB")
            if img.mode == "L" and not alpha:
                mode = "L"
            img = img.convert(mode)
            clean = Image.frombytes(mode, img.size, img.tobytes())  # pixels only: no EXIF, XMP, ICC or comments
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError) as e:
        raise NotUsable("That photo couldn't be opened. Please try a different file.") from e
    out = io.BytesIO()
    options = {"quality": 92, "optimize": True} if fmt == "JPEG" else {"quality": 92} if fmt == "WEBP" else {"optimize": True}
    clean.save(out, format=fmt, **options)
    content_type, ext = PHOTO_FORMATS[fmt]
    return out.getvalue(), content_type, ext


def temporary_file(suffix: str = "") -> Path:
    """A new, empty, private temporary file. (Closed straight away: Windows can't reuse or delete an open file.)"""
    handle, name = tempfile.mkstemp(suffix=suffix)
    os.close(handle)
    return Path(name)


# ─── Videos ───────────────────────────────────────────────────────────────────
def ffmpeg() -> str:
    """The ffmpeg program that comes with imageio-ffmpeg (no system install needed)."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:  # not installed, or no binary for this system
        raise VideoUnavailable("Video uploads aren't available on this server yet.") from e


def clean_video(source: Path, head: bytes, keep_sound: bool = True) -> tuple[Path, str, str]:
    """
    The video re-packed without metadata or extra tracks, as a new temporary file: (path, content type,
    extension). The caller moves or deletes it.
    """
    container = "webm" if head[:4] == b"\x1a\x45\xdf\xa3" else "mp4"
    content_type, ext = VIDEO_FORMATS[container]
    target = temporary_file(f".{ext}")
    command = [ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
               "-map", "0:v:0", *(["-map", "0:a?"] if keep_sound else ["-an"]),   # the picture (and sound), nothing else
               "-c", "copy",                                                     # no re-encoding: quick, no quality loss
               "-map_metadata", "-1", "-map_metadata:s:v", "-1", "-map_metadata:s:a", "-1", "-map_chapters", "-1",
               "-fflags", "+bitexact", "-flags:v", "+bitexact", "-flags:a", "+bitexact"]
    command += ["-movflags", "+faststart", "-f", "mp4"] if container == "mp4" else ["-f", "webm"]
    try:
        done = subprocess.run(command + [str(target)], capture_output=True, timeout=180)
    except subprocess.TimeoutExpired as e:
        target.unlink(missing_ok=True)
        raise NotUsable("That video took too long to process. Please try a shorter clip.") from e
    except OSError as e:  # ffmpeg couldn't be started (e.g. blocked by the operating system)
        target.unlink(missing_ok=True)
        raise VideoUnavailable("Video uploads aren't available on this server yet.") from e
    if done.returncode != 0 or target.stat().st_size == 0:
        target.unlink(missing_ok=True)
        raise NotUsable("That video couldn't be processed. Please try an MP4 or WebM file.")
    return target, content_type, ext


# ─── Storing and listing ──────────────────────────────────────────────────────
def path_of(item: Evidence) -> Path:
    return EVIDENCE_DIR / item.stored_name


def listing(db: Session, case_id: str) -> list[dict]:
    """The case's evidence, in the order it was added (what both the reporter and HR see about each file)."""
    items = db.scalars(select(Evidence).where(Evidence.case_id == case_id).order_by(Evidence.number))
    return [{"id": e.id, "number": e.number, "kind": e.kind, "content_type": e.content_type, "size": e.size,
             "added_on": e.added_on.isoformat()} for e in items]


def store(db: Session, case_id: str, kind: str, content_type: str, ext: str, data: bytes | None = None,
          move_from: Path | None = None, today: date | None = None) -> Evidence:
    """Save a cleaned file under a random name and record it."""
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    item_id = secrets.token_hex(16)
    name = f"{item_id}.{ext}"
    if move_from is not None:
        shutil.move(str(move_from), EVIDENCE_DIR / name)  # works across drives, unlike a rename
    else:
        (EVIDENCE_DIR / name).write_bytes(data)
    last = db.scalar(select(Evidence.number).where(Evidence.case_id == case_id).order_by(Evidence.number.desc()).limit(1))
    item = Evidence(id=item_id, case_id=case_id, number=(last or 0) + 1, kind=kind, content_type=content_type,
                    size=(EVIDENCE_DIR / name).stat().st_size, stored_name=name, added_on=today or date.today())
    db.add(item)
    return item
