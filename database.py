import datetime
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# SQLite Database URL (creates kq_chatbot.db in project root)
SQLALCHEMY_DATABASE_URL = "sqlite:///./kq_chatbot.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}  # Required for SQLite in FastAPI
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ---------------------------------------------------------
# Database Models
# ---------------------------------------------------------

class StaffMember(Base):
    __tablename__ = "staff_members"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(String, unique=True, index=True, nullable=False) # e.g., KQ-8842
    full_name = Column(String, nullable=False)                         # e.g., Jane Doe
    department = Column(String, nullable=False)                        # e.g., Ground Ops, Cabin Crew
    role = Column(String, nullable=False)                              # e.g., Flight Attendant, Duty Manager
    is_active = Column(Boolean, default=True)

    rosters = relationship("ShiftRoster", back_populates="staff_member")


class ShiftRoster(Base):
    __tablename__ = "shift_rosters"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(String, ForeignKey("staff_members.staff_id"), nullable=False)
    shift_date = Column(String, nullable=False)                         # e.g., 2026-10-30
    shift_time = Column(String, nullable=False)                         # e.g., 06:00 AM - 02:00 PM
    assigned_flight = Column(String, nullable=True)                     # e.g., KQ100
    location = Column(String, nullable=False)                            # e.g., Terminal 1A Gate 4
    duty_summary = Column(String, nullable=False)                       # e.g., Boarding & Passenger Clearance

    staff_member = relationship("StaffMember", back_populates="rosters")


# Helper function to create all tables and populate initial mock data
def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Check if seed data exists
    if not db.query(StaffMember).first():
        sample_staff = [
            StaffMember(staff_id="KQ-8842", full_name="Nicholas Nyukuri", department="Flight Operations", role="Lead Dispatcher"),
            StaffMember(staff_id="KQ-1009", full_name="Amina Mohamed", department="Ground Handling", role="Gate Supervisor"),
            StaffMember(staff_id="KQ-5521", full_name="Kevin Mandela", department="Engineering", role="Avionics Technician"),
        ]
        db.add_all(sample_staff)
        db.commit()

        sample_rosters = [
            ShiftRoster(staff_id="KQ-8842", shift_date="2026-10-30", shift_time="06:00 AM - 02:00 PM", assigned_flight="KQ100", location="JKIA Terminal 1A", duty_summary="Dispatch & Flight Clearance"),
            ShiftRoster(staff_id="KQ-8842", shift_date="2026-10-31", shift_time="02:00 PM - 10:00 PM", assigned_flight="KQ102", location="JKIA Control Center", duty_summary="Flight Monitoring"),
            ShiftRoster(staff_id="KQ-1009", shift_date="2026-10-30", shift_time="08:00 AM - 04:00 PM", assigned_flight="KQ305", location="Gate 4", duty_summary="Passenger Boarding Clearance"),
            ShiftRoster(staff_id="KQ-5521", shift_date="2026-10-30", shift_time="10:00 PM - 06:00 AM", assigned_flight="KQ100", location="Hangar 2", duty_summary="Pre-flight Avionics Inspection"),
        ]
        db.add_all(sample_rosters)
        db.commit()
    db.close()