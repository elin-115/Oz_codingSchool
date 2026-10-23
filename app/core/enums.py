from enum import StrEnum


class Gender(StrEnum):
    M = "male"
    F = "female"


class Department(StrEnum):
    DEV = "developer"  # 개발자
    MEDICAL = "medical team"  # 의료진
    RESEARCH = "researcher"  # 연구진


class UserRole(StrEnum):
    PENDING = "pending"  # 가입 승인 대기
    STAFF = "staff"
    ADMIN = "admin"
