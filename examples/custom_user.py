# Example of extending the BaseUser model
from models.user import BaseUser, create_extended_user_model
from utils.types import Field


class ExtendedUser(BaseUser):
    """Example of an extended user model"""
    _columns = {
        **BaseUser._columns,
        'phone_number': Field('TEXT', nullable=True),
        'date_of_birth': Field('DATE', nullable=True),
        'bio': Field('TEXT', nullable=True)
    }

# Example of using the factory to create a user model
StudentUser = create_extended_user_model(
    "StudentUser",
    {
        'student_id': Field('TEXT', unique=True, index=True),
        'major': Field('TEXT'),
        'gpa': Field('FLOAT', default=0.0)
    }
)

TeacherUser = create_extended_user_model(
    "TeacherUser",
    {
        'employee_id': Field('TEXT', unique=True, index=True),
        'department': Field('TEXT'),
        'salary': Field('FLOAT', default=0.0)
    }
)