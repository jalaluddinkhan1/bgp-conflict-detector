"""
InfluxDB client for time-series storage.
"""
from typing import Any, Optional

from influxdb_client import InfluxDBClient as InfluxClient
from influxdb_client.client.write_api import SYNCHRONOUS


class InfluxDBClient:
    """
    InfluxDB client for storing time-series BGP data.
    
    Used for storing metrics, updates, and historical data
    for analysis and monitoring.
    """

    def __init__(
        self,
        url: str,
        token: str,
        org: str,
        bucket: str,
        timeout: int = 10000,
    ):
        """
        Initialize InfluxDB client.
        
        Args:
            url: InfluxDB server URL
            token: Authentication token
            org: Organization name
            bucket: Bucket name for data
            timeout: Request timeout in milliseconds
        """
        self.client = InfluxClient(url=url, token=token, org=org, timeout=timeout)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.query_api = self.client.query_api()
        self.bucket = bucket
        self.org = org

    def write_point(
        self,
        measurement: str,
        tags: dict[str, str],
        fields: dict[str, Any],
        timestamp: Optional[int] = None,
    ) -> None:
        """
        Write a data point to InfluxDB.
        
        Args:
            measurement: Measurement name
            tags: Tags dictionary
            fields: Fields dictionary
            timestamp: Timestamp in nanoseconds (optional, defaults to now)
        """
        from influxdb_client import Point

        point = Point(measurement)
        for key, value in tags.items():
            point = point.tag(key, value)
        for key, value in fields.items():
            point = point.field(key, value)
        if timestamp:
            point = point.time(timestamp)

        self.write_api.write(bucket=self.bucket, org=self.org, record=point)

    def write_bgp_update(
        self,
        peer_ip: str,
        asn: int,
        prefix: str,
        update_type: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Write BGP update to InfluxDB.
        
        Args:
            peer_ip: Peer IP address
            asn: Autonomous System Number
            prefix: Network prefix
            update_type: Type of update (announce/withdraw)
            metadata: Additional metadata
        """
        tags = {
            "peer_ip": peer_ip,
            "asn": str(asn),
            "prefix": prefix,
        }
        fields = {
            "update_type": update_type,
        }
        if metadata:
            fields.update(metadata)

        self.write_point("bgp_updates", tags, fields)

    def query(self, query: str) -> list[dict[str, Any]]:
        """
        Execute Flux query.
        
        Args:
            query: Flux query string
            
        Returns:
            List of result dictionaries
        """
        result = self.query_api.query(org=self.org, query=query)
        results = []
        for table in result:
            for record in table.records:
                results.append(record.values)
        return results

    def close(self) -> None:
        """Close InfluxDB client connections."""
        self.write_api.close()
        self.client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

