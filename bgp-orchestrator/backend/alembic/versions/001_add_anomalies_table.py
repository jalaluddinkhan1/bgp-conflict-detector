"""Add anomalies table

Revision ID: 001_add_anomalies
Revises: 
Create Date: 2024-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_add_anomalies'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create anomaly_type enum (only if it doesn't exist)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE anomaly_type AS ENUM (
                'bgp_flap',
                'cpu_temperature',
                'interface_error',
                'other'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create anomaly_severity enum (only if it doesn't exist)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE anomaly_severity AS ENUM (
                'low',
                'medium',
                'high',
                'critical'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create anomalies table
    op.create_table(
        'anomalies',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('metric_name', sa.String(length=255), nullable=False),
        sa.Column('anomaly_type', postgresql.ENUM(
            'bgp_flap', 'cpu_temperature', 'interface_error', 'other',
            name='anomaly_type', create_type=False
        ), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('expected_value', sa.Float(), nullable=False),
        sa.Column('deviation', sa.Float(), nullable=False),
        sa.Column('severity', postgresql.ENUM(
            'low', 'medium', 'high', 'critical',
            name='anomaly_severity', create_type=False
        ), nullable=False),
        sa.Column('device', sa.String(length=255), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_anomalies_id', 'anomalies', ['id'], unique=False)
    op.create_index('ix_anomalies_metric_name', 'anomalies', ['metric_name'], unique=False)
    op.create_index('ix_anomalies_anomaly_type', 'anomalies', ['anomaly_type'], unique=False)
    op.create_index('ix_anomalies_timestamp', 'anomalies', ['timestamp'], unique=False)
    op.create_index('ix_anomalies_severity', 'anomalies', ['severity'], unique=False)
    op.create_index('ix_anomalies_device', 'anomalies', ['device'], unique=False)
    op.create_index('idx_anomaly_metric_timestamp', 'anomalies', ['metric_name', 'timestamp'], unique=False)
    op.create_index('idx_anomaly_device_timestamp', 'anomalies', ['device', 'timestamp'], unique=False)
    op.create_index('idx_anomaly_severity_timestamp', 'anomalies', ['severity', 'timestamp'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_anomaly_severity_timestamp', table_name='anomalies')
    op.drop_index('idx_anomaly_device_timestamp', table_name='anomalies')
    op.drop_index('idx_anomaly_metric_timestamp', table_name='anomalies')
    op.drop_index('ix_anomalies_device', table_name='anomalies')
    op.drop_index('ix_anomalies_severity', table_name='anomalies')
    op.drop_index('ix_anomalies_timestamp', table_name='anomalies')
    op.drop_index('ix_anomalies_anomaly_type', table_name='anomalies')
    op.drop_index('ix_anomalies_metric_name', table_name='anomalies')
    op.drop_index('ix_anomalies_id', table_name='anomalies')
    
    # Drop table
    op.drop_table('anomalies')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS anomaly_severity')
    op.execute('DROP TYPE IF EXISTS anomaly_type')

