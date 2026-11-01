"""Create V1 Social Circle Calendar schema.

Revision ID: 0001_initial
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


connection_status = sa.Enum("PENDING", "ACCEPTED", "DECLINED", name="connection_status")
event_category = sa.Enum("SPORTS", "FOOD", "ART", "SOCIAL", name="event_category")
event_status = sa.Enum("ACTIVE", "CANCELLED", name="event_status")
participant_status = sa.Enum("ACTIVE", "LEFT", name="participant_status")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("nickname", sa.String(40), nullable=False),
        sa.Column("gender", sa.String(40)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_nickname", "users", ["nickname"])
    op.create_table(
        "connections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_low_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_high_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requester_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", connection_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("user_low_id < user_high_id", name="ck_connection_canonical_order"),
        sa.UniqueConstraint("user_low_id", "user_high_id", name="uq_connection_pair"),
    )
    op.create_index("ix_connections_status_low", "connections", ["status", "user_low_id"])
    op.create_index("ix_connections_status_high", "connections", ["status", "user_high_id"])
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("creator_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("description", sa.String(2000), nullable=False),
        sa.Column("category", event_category, nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location", sa.String(200), nullable=False),
        sa.Column("status", event_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("ends_at > starts_at", name="ck_event_end_after_start"),
    )
    op.create_index("ix_events_creator_id", "events", ["creator_id"])
    op.create_index("ix_events_active_start", "events", ["status", "starts_at"])
    op.create_table(
        "participants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", participant_status, nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("left_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("event_id", "user_id", name="uq_event_participant"),
    )
    op.create_index("ix_participants_user_status", "participants", ["user_id", "status"])
    op.create_table(
        "event_invitations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invited_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("event_id", "user_id", name="uq_event_invitation"),
    )
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("leave_action_id", sa.String(36), nullable=False),
        sa.Column("recipient_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("leave_action_id", "recipient_id", name="uq_leave_notification"),
    )
    op.create_index("ix_notifications_recipient_id", "notifications", ["recipient_id"])


def downgrade() -> None:
    op.drop_index("ix_notifications_recipient_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_table("event_invitations")
    op.drop_index("ix_participants_user_status", table_name="participants")
    op.drop_table("participants")
    op.drop_index("ix_events_active_start", table_name="events")
    op.drop_index("ix_events_creator_id", table_name="events")
    op.drop_table("events")
    op.drop_index("ix_connections_status_high", table_name="connections")
    op.drop_index("ix_connections_status_low", table_name="connections")
    op.drop_table("connections")
    op.drop_index("ix_users_nickname", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    bind = op.get_bind()
    participant_status.drop(bind, checkfirst=True)
    event_status.drop(bind, checkfirst=True)
    event_category.drop(bind, checkfirst=True)
    connection_status.drop(bind, checkfirst=True)
