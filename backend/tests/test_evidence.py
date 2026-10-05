"""Evidence for reports: photos and videos lose their hidden details before they're saved, and only the reporter
(with their key) and HR can see them."""
import io
import os
import subprocess
from pathlib import Path

import pytest
from PIL import Image, PngImagePlugin

from app.reporting import evidence
from tests.conftest import login

TEXT = "My manager shouted at me and humiliated me in front of the whole team again this week."


def new_case(client):
    return client.post("/api/reports", headers=login(client, "employee"), json={"category": "bullying", "text": TEXT}).json()


def upload(client, case, data, name="IMG_Jane_Doe_2026-03-01.jpg", key=None, **form):
    return client.post("/api/reports/evidence", headers=login(client, "employee"),
                       data={"case_id": case["case_id"], "key": key or case["key"], **form},
                       files={"file": (name, data, "application/octet-stream")})


def phone_photo(orientation=6) -> bytes:
    """A JPEG like a phone's: GPS position, make, model, owner, the time taken, and a rotation tag."""
    img = Image.new("RGB", (40, 20), (200, 30, 30))
    exif = Image.Exif()
    exif[0x010F], exif[0x0110], exif[0x013B] = "Apple", "iPhone 15", "Jane Doe"   # make, model, artist
    exif[0x0132], exif[0x0112] = "2026:03:01 09:14:00", orientation             # date taken, orientation
    exif[0x8825] = {1: "N", 2: (51.0, 30.0, 26.0), 3: "W", 4: (0.0, 7.0, 39.0)}   # GPS
    out = io.BytesIO()
    img.save(out, format="JPEG", exif=exif, comment=b"Phone of Jane")
    return out.getvalue()


def stored_files():
    folder = Path(os.environ["EVIDENCE_DIR"])
    return sorted(folder.iterdir()) if folder.exists() else []


@pytest.fixture(autouse=True)
def empty_evidence_folder():
    for f in stored_files():
        f.unlink()


# ─── Photos ───────────────────────────────────────────────────────────────────
def test_a_photo_loses_its_location_device_and_owner(client):
    photo = phone_photo()
    assert b"Jane" in photo and b"iPhone" in photo
    case = new_case(client)
    res = upload(client, case, photo)
    assert res.status_code == 201, res.text
    item = res.json()["evidence"][0]
    assert item["kind"] == "photo" and item["content_type"] == "image/jpeg" and item["number"] == 1
    saved = client.get(f"/api/hr/reports/{case['case_id']}/evidence/{item['id']}", headers=login(client, "hr"))
    assert saved.status_code == 200 and saved.headers["cache-control"] == "no-store"
    img = Image.open(io.BytesIO(saved.content))
    assert len(img.getexif()) == 0 and not {"exif", "comment", "xmp", "icc_profile"} & set(img.info)
    assert b"Jane" not in saved.content and b"iPhone" not in saved.content
    assert img.size == (20, 40)  # turned the right way up before the rotation tag was removed


def test_png_text_is_removed(client):
    info = PngImagePlugin.PngInfo()
    info.add_text("Author", "Jane Doe")
    out = io.BytesIO()
    Image.new("RGBA", (10, 10), (0, 0, 255, 128)).save(out, format="PNG", pnginfo=info)
    case = new_case(client)
    item = upload(client, case, out.getvalue(), name="screenshot.png").json()["evidence"][0]
    saved = client.get(f"/api/hr/reports/{case['case_id']}/evidence/{item['id']}", headers=login(client, "hr")).content
    assert b"Jane" not in saved and Image.open(io.BytesIO(saved)).mode == "RGBA"


def test_the_original_file_name_is_never_kept(client):
    case = new_case(client)
    upload(client, case, phone_photo())
    files = stored_files()
    assert files and all("Jane" not in f.name and "2026" not in f.name for f in files)
    detail = client.get(f"/api/hr/reports/{case['case_id']}", headers=login(client, "hr")).json()
    assert "Jane" not in str(detail["evidence"])


@pytest.mark.parametrize("data, name", [
    (b"<html><script>alert(1)</script></html>", "photo.jpg"),   # disguised by its name
    (b"%PDF-1.7 not a photo", "evidence.pdf"),
    (b"\xff\xd8\xff\xe0 broken jpeg", "broken.jpg"),            # starts like a JPEG but isn't one
])
def test_only_real_photos_and_videos_are_accepted(client, data, name):
    case = new_case(client)
    assert upload(client, case, data, name=name).status_code == 422
    assert stored_files() == []


def test_files_that_are_too_big_are_refused(client, monkeypatch):
    monkeypatch.setattr(evidence, "MAX_PHOTO_BYTES", 500)
    case = new_case(client)
    res = upload(client, case, phone_photo() + b"\0" * 1000)
    assert res.status_code == 413 and "MB" in res.json()["detail"]


def test_a_case_holds_a_limited_number_of_files(client, monkeypatch):
    monkeypatch.setattr(evidence, "MAX_FILES", 2)
    case = new_case(client)
    assert [upload(client, case, phone_photo()).status_code for _ in range(3)] == [201, 201, 409]


# ─── Who can see and change evidence ──────────────────────────────────────────
def test_the_key_is_needed_to_add_or_see_evidence(client):
    case = new_case(client)
    assert upload(client, case, phone_photo(), key="WRONG-KEY0-0000-0000").status_code == 403
    item = upload(client, case, phone_photo()).json()["evidence"][0]
    body = {"case_id": case["case_id"], "key": case["key"]}
    assert client.post(f"/api/reports/evidence/{item['id']}/view", headers=login(client, "employee"), json=body).status_code == 200
    body["key"] = "WRONG-KEY0-0000-0000"
    assert client.post(f"/api/reports/evidence/{item['id']}/view", headers=login(client, "employee"), json=body).status_code == 403


@pytest.mark.parametrize("username", ["employee", "manager", "admin"])
def test_only_hr_opens_evidence_without_a_key(client, username):
    case = new_case(client)
    item = upload(client, case, phone_photo()).json()["evidence"][0]
    assert client.get(f"/api/hr/reports/{case['case_id']}/evidence/{item['id']}", headers=login(client, username)).status_code == 403


def test_evidence_from_another_case_cant_be_opened_through_this_one(client):
    first, second = new_case(client), new_case(client)
    item = upload(client, first, phone_photo()).json()["evidence"][0]
    body = {"case_id": second["case_id"], "key": second["key"]}
    assert client.post(f"/api/reports/evidence/{item['id']}/view", headers=login(client, "employee"), json=body).status_code == 404


def test_the_reporter_sees_and_removes_their_files(client):
    case = new_case(client)
    item = upload(client, case, phone_photo()).json()["evidence"][0]
    body = {"case_id": case["case_id"], "key": case["key"]}
    view = client.post("/api/reports/access", headers=login(client, "employee"), json=body).json()
    assert [e["id"] for e in view["evidence"]] == [item["id"]]
    left = client.post(f"/api/reports/evidence/{item['id']}/remove", headers=login(client, "employee"), json=body)
    assert left.status_code == 200 and left.json()["evidence"] == [] and stored_files() == []


def test_hr_sees_how_many_files_each_case_has(client):
    case = new_case(client)
    upload(client, case, phone_photo())
    inbox = client.get("/api/hr/reports", headers=login(client, "hr")).json()
    assert next(r for r in inbox if r["case_id"] == case["case_id"])["evidence_count"] == 1


def test_nothing_can_be_added_to_a_closed_case(client):
    case = new_case(client)
    client.patch(f"/api/hr/reports/{case['case_id']}", headers=login(client, "hr"), json={"outcome": "resolved", "status": "closed"})
    assert upload(client, case, phone_photo()).status_code == 409


# ─── Videos ───────────────────────────────────────────────────────────────────
def ffmpeg_or_skip():
    try:
        return evidence.ffmpeg()
    except evidence.VideoUnavailable:
        pytest.skip("ffmpeg isn't available here")


def phone_video(tmp_path) -> bytes:
    """A short MOV with a location, an owner and a recording time, like a phone's."""
    path = tmp_path / "clip.mov"
    subprocess.run([ffmpeg_or_skip(), "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=160x120:rate=10",
                    "-f", "lavfi", "-i", "sine", "-t", "1", "-c:v", "libx264", "-c:a", "aac",
                    "-metadata", "location=+51.5072-000.1276/", "-metadata", "comment=Jane Doe iPhone",
                    "-metadata", "creation_time=2026-03-01T09:14:00Z", "-movflags", "use_metadata_tags", str(path)], check=True)
    return path.read_bytes()


def streams(tmp_path, data: bytes) -> str:
    path = tmp_path / "check.mp4"
    path.write_bytes(data)
    return subprocess.run([evidence.ffmpeg(), "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr


@pytest.mark.parametrize("keep_sound", [True, False])
def test_a_video_loses_its_location_and_owner(client, tmp_path, keep_sound):
    video = phone_video(tmp_path)
    assert b"Jane" in video and b"51.5072" in video
    case = new_case(client)
    res = upload(client, case, video, name="VID_2026.mov", keep_sound=str(keep_sound).lower())
    assert res.status_code == 201, res.text
    item = res.json()["evidence"][0]
    assert item["kind"] == "video" and item["content_type"] == "video/mp4"
    saved = client.get(f"/api/hr/reports/{case['case_id']}/evidence/{item['id']}", headers=login(client, "hr")).content
    assert b"Jane" not in saved and b"51.5072" not in saved and b"2026-03-01" not in saved
    info = streams(tmp_path, saved)
    assert "Video:" in info and ("Audio:" in info) == keep_sound
