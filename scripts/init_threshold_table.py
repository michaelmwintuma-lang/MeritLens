import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
os.environ["SKIP_ENV_FILE"] = "0"

from app.core.database import engine, Base
from app.governance.models import ThresholdPolicy

Base.metadata.create_all(engine)
print("threshold_policy table ensured in app.db successfully!")
