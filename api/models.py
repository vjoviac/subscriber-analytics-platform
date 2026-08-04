from datetime import datetime

from pydantic import BaseModel


class SubscriberDetails(BaseModel):
    imsi: str
    msisdn: str
    plan: str


class DeviceDetails(BaseModel):
    tac: str
    vendor: str
    model: str
    os: str
    capability: str


class NetworkState(BaseModel):
    technology: str
    cell_id: str
    city: str
    state: str
    country: str | None


class ActivityMetrics(BaseModel):
    first_activity_at: datetime
    last_activity_at: datetime
    active_day_count: int
    lifetime_event_count: int
    total_bytes_dl: int
    total_bytes_ul: int
    total_bytes: int
    latency_sum: float
    latency_sample_count: int
    avg_latency_ms: float | None
    packet_loss_sum: float
    packet_loss_sample_count: int
    avg_packet_loss_pct: float | None


class ProfileMetadata(BaseModel):
    profile_version: int
    profile_updated_at: datetime


class SubscriberProfileResponse(BaseModel):
    subscriber_id: str
    subscriber: SubscriberDetails
    device: DeviceDetails
    last_network_state: NetworkState
    activity: ActivityMetrics
    metadata: ProfileMetadata

class PaginationMetadata(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int


class SubscriberProfileListResponse(BaseModel):
    items: list[SubscriberProfileResponse]
    pagination: PaginationMetadata

class ErrorResponse(BaseModel):
    detail: str

