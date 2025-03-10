# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License
import asyncio
import io
import os
import random
import sys
import time
import unittest
import uuid

import pytest
from azure.kusto.data import KustoClient, KustoConnectionStringBuilder
from azure.kusto.data._cloud_settings import CloudSettings
from azure.kusto.data.aio import KustoClient as AsyncKustoClient
from azure.kusto.data.exceptions import KustoServiceError

from azure.kusto.ingest import (
    QueuedIngestClient,
    KustoStreamingIngestClient,
    IngestionProperties,
    DataFormat,
    ColumnMapping,
    IngestionMappingType,
    ValidationPolicy,
    ValidationOptions,
    ValidationImplications,
    ReportLevel,
    ReportMethod,
    FileDescriptor,
)

CLEAR_DB_CACHE = ".clear database cache streamingingestion schema"


class TestE2E:
    """A class to define mappings to deft table."""

    @staticmethod
    def get_test_table_csv_mappings():
        """A method to define csv mappings to test table."""
        mappings = list()
        mappings.append(ColumnMapping(column_name="rownumber", column_type="int", ordinal=0))
        mappings.append(ColumnMapping(column_name="rowguid", column_type="string", ordinal=1))
        mappings.append(ColumnMapping(column_name="xdouble", column_type="real", ordinal=2))
        mappings.append(ColumnMapping(column_name="xfloat", column_type="real", ordinal=3))
        mappings.append(ColumnMapping(column_name="xbool", column_type="bool", ordinal=4))
        mappings.append(ColumnMapping(column_name="xint16", column_type="int", ordinal=5))
        mappings.append(ColumnMapping(column_name="xint32", column_type="int", ordinal=6))
        mappings.append(ColumnMapping(column_name="xint64", column_type="long", ordinal=7))
        mappings.append(ColumnMapping(column_name="xuint8", column_type="long", ordinal=8))
        mappings.append(ColumnMapping(column_name="xuint16", column_type="long", ordinal=9))
        mappings.append(ColumnMapping(column_name="xuint32", column_type="long", ordinal=10))
        mappings.append(ColumnMapping(column_name="xuint64", column_type="long", ordinal=11))
        mappings.append(ColumnMapping(column_name="xdate", column_type="datetime", ordinal=12))
        mappings.append(ColumnMapping(column_name="xsmalltext", column_type="string", ordinal=13))
        mappings.append(ColumnMapping(column_name="xtext", column_type="string", ordinal=14))
        mappings.append(ColumnMapping(column_name="xnumberAsText", column_type="string", ordinal=15))
        mappings.append(ColumnMapping(column_name="xtime", column_type="timespan", ordinal=16))
        mappings.append(ColumnMapping(column_name="xtextWithNulls", column_type="string", ordinal=17))
        mappings.append(ColumnMapping(column_name="xdynamicWithNulls", column_type="dynamic", ordinal=18))
        return mappings

    @staticmethod
    def test_table_json_mappings():
        """A method to define json mappings to test table."""
        mappings = list()
        mappings.append(ColumnMapping(column_name="rownumber", path="$.rownumber", column_type="int"))
        mappings.append(ColumnMapping(column_name="rowguid", path="$.rowguid", column_type="string"))
        mappings.append(ColumnMapping(column_name="xdouble", path="$.xdouble", column_type="real"))
        mappings.append(ColumnMapping(column_name="xfloat", path="$.xfloat", column_type="real"))
        mappings.append(ColumnMapping(column_name="xbool", path="$.xbool", column_type="bool"))
        mappings.append(ColumnMapping(column_name="xint16", path="$.xint16", column_type="int"))
        mappings.append(ColumnMapping(column_name="xint32", path="$.xint32", column_type="int"))
        mappings.append(ColumnMapping(column_name="xint64", path="$.xint64", column_type="long"))
        mappings.append(ColumnMapping(column_name="xuint8", path="$.xuint8", column_type="long"))
        mappings.append(ColumnMapping(column_name="xuint16", path="$.xuint16", column_type="long"))
        mappings.append(ColumnMapping(column_name="xuint32", path="$.xuint32", column_type="long"))
        mappings.append(ColumnMapping(column_name="xuint64", path="$.xuint64", column_type="long"))
        mappings.append(ColumnMapping(column_name="xdate", path="$.xdate", column_type="datetime"))
        mappings.append(ColumnMapping(column_name="xsmalltext", path="$.xsmalltext", column_type="string"))
        mappings.append(ColumnMapping(column_name="xtext", path="$.xtext", column_type="string"))
        mappings.append(ColumnMapping(column_name="xnumberAsText", path="$.xnumberAsText", column_type="string"))
        mappings.append(ColumnMapping(column_name="xtime", path="$.xtime", column_type="timespan"))
        mappings.append(ColumnMapping(column_name="xtextWithNulls", path="$.xtextWithNulls", column_type="string"))
        mappings.append(ColumnMapping(column_name="xdynamicWithNulls", path="$.xdynamicWithNulls", column_type="dynamic"))
        return mappings

    @staticmethod
    def test_table_json_mapping_reference():
        """A method to get json mappings reference to test table."""
        return """'['
                    '    { "column" : "rownumber", "datatype" : "int", "Properties":{"Path":"$.rownumber"}},'
                    '    { "column" : "rowguid", "datatype" : "string", "Properties":{"Path":"$.rowguid"}},'
                    '    { "column" : "xdouble", "datatype" : "real", "Properties":{"Path":"$.xdouble"}},'
                    '    { "column" : "xfloat", "datatype" : "real", "Properties":{"Path":"$.xfloat"}},'
                    '    { "column" : "xbool", "datatype" : "bool", "Properties":{"Path":"$.xbool"}},'
                    '    { "column" : "xint16", "datatype" : "int", "Properties":{"Path":"$.xint16"}},'
                    '    { "column" : "xint32", "datatype" : "int", "Properties":{"Path":"$.xint32"}},'
                    '    { "column" : "xint64", "datatype" : "long", "Properties":{"Path":"$.xint64"}},'
                    '    { "column" : "xuint8", "datatype" : "long", "Properties":{"Path":"$.xuint8"}},'
                    '    { "column" : "xuint16", "datatype" : "long", "Properties":{"Path":"$.xuint16"}},'
                    '    { "column" : "xuint32", "datatype" : "long", "Properties":{"Path":"$.xuint32"}},'
                    '    { "column" : "xuint64", "datatype" : "long", "Properties":{"Path":"$.xuint64"}},'
                    '    { "column" : "xdate", "datatype" : "datetime", "Properties":{"Path":"$.xdate"}},'
                    '    { "column" : "xsmalltext", "datatype" : "string", "Properties":{"Path":"$.xsmalltext"}},'
                    '    { "column" : "xtext", "datatype" : "string", "Properties":{"Path":"$.xtext"}},'
                    '    { "column" : "xnumberAsText", "datatype" : "string", "Properties":{"Path":"$.rowguid"}},'
                    '    { "column" : "xtime", "datatype" : "timespan", "Properties":{"Path":"$.xtime"}},'
                    '    { "column" : "xtextWithNulls", "datatype" : "string", "Properties":{"Path":"$.xtextWithNulls"}},'
                    '    { "column" : "xdynamicWithNulls", "datatype" : "dynamic", "Properties":{"Path":"$.xdynamicWithNulls"}},'
                    ']'"""

    @staticmethod
    def get_file_path() -> str:
        current_dir = os.getcwd()
        path_parts = ["azure-kusto-ingest", "tests", "input"]
        missing_path_parts = []
        for path_part in path_parts:
            if path_part not in current_dir:
                missing_path_parts.append(path_part)
        return os.path.join(current_dir, *missing_path_parts)

    @classmethod
    def engine_kcsb_from_env(cls) -> KustoConnectionStringBuilder:
        if all([cls.app_id, cls.app_key, cls.auth_id]):
            return KustoConnectionStringBuilder.with_aad_application_key_authentication(cls.engine_cs, cls.app_id, cls.app_key, cls.auth_id)
        else:
            return KustoConnectionStringBuilder.with_interactive_login(cls.engine_cs)

    @classmethod
    def dm_kcsb_from_env(cls) -> KustoConnectionStringBuilder:
        if all([cls.app_id, cls.app_key, cls.auth_id]):
            return KustoConnectionStringBuilder.with_aad_application_key_authentication(cls.dm_cs, cls.app_id, cls.app_key, cls.auth_id)
        else:
            return KustoConnectionStringBuilder.with_interactive_login(cls.dm_cs)

    @classmethod
    def setup_class(cls):
        # DM CS can be composed from engine CS
        cls.engine_cs = os.environ.get("ENGINE_CONNECTION_STRING")
        cls.dm_cs = os.environ.get("DM_CONNECTION_STRING") or cls.engine_cs.replace("//", "//ingest-")
        cls.app_id = os.environ.get("APP_ID")
        cls.app_key = os.environ.get("APP_KEY")
        cls.auth_id = os.environ.get("AUTH_ID")
        cls.test_db = os.environ.get("TEST_DATABASE")

        if not all([cls.engine_cs, cls.dm_cs, cls.test_db]):
            raise unittest.SkipTest("E2E environment is missing")

        # Init clients
        python_version = "_".join([str(v) for v in sys.version_info[:3]])
        cls.test_table = "python_test_{0}_{1}_{2}".format(python_version, str(int(time.time())), random.randint(1, 100000))
        cls.client = KustoClient(cls.engine_kcsb_from_env())
        cls.ingest_client = QueuedIngestClient(cls.dm_kcsb_from_env())
        cls.streaming_ingest_client = KustoStreamingIngestClient(cls.engine_kcsb_from_env())
        cls.async_client_lock = asyncio.Lock()
        cls.async_client = None  # async client needs to be initialized in an async context, so instead of
        # initializing it here we use a lazy function get_async_client

        cls.input_folder_path = cls.get_file_path()

        cls.csv_file_path = os.path.join(cls.input_folder_path, "dataset.csv")
        cls.tsv_file_path = os.path.join(cls.input_folder_path, "dataset.tsv")
        cls.zipped_csv_file_path = os.path.join(cls.input_folder_path, "dataset.csv.gz")
        cls.json_file_path = os.path.join(cls.input_folder_path, "dataset.json")
        cls.zipped_json_file_path = os.path.join(cls.input_folder_path, "dataset.jsonz.gz")

        cls.current_count = 0

        cls.client.execute(
            cls.test_db,
            ".create table {0} (rownumber: int, rowguid: string, xdouble: real, xfloat: real, xbool: bool, xint16: int, xint32: int, xint64: long, xuint8: long, xuint16: long, xuint32: long, xuint64: long, xdate: datetime, xsmalltext: string, xtext: string, xnumberAsText: string, xtime: timespan, xtextWithNulls: string, xdynamicWithNulls: dynamic)".format(
                cls.test_table
            ),
        )
        cls.client.execute(
            cls.test_db, ".create table {0} ingestion json mapping 'JsonMapping' {1}".format(cls.test_table, cls.test_table_json_mapping_reference())
        )

    @classmethod
    def teardown_class(cls):
        cls.client.execute(cls.test_db, ".drop table {} ifexists".format(cls.test_table))

    @classmethod
    async def get_async_client(cls) -> AsyncKustoClient:
        async with cls.async_client_lock:
            if cls.async_client:
                return cls.async_client
            return AsyncKustoClient(cls.engine_kcsb_from_env())

    # assertions
    @classmethod
    async def assert_rows_added(cls, expected: int, timeout=60):
        actual = 0
        while timeout > 0:
            time.sleep(1)
            timeout -= 1

            try:
                command = "{} | count".format(cls.test_table)
                response = cls.client.execute(cls.test_db, command)
                async_client = await cls.get_async_client()
                response_from_async = await async_client.execute(cls.test_db, command)
            except KustoServiceError:
                continue

            if response is not None:
                row = response.primary_results[0][0]
                row_async = response_from_async.primary_results[0][0]
                actual = int(row["Count"]) - cls.current_count
                # this is done to allow for data to arrive properly
                if actual >= expected:
                    assert row_async == row, "Mismatch answers between async('{0}') and sync('{1}') clients".format(
                        row_async.primary_results, row.primary_results
                    )
                    break

        cls.current_count += actual
        assert actual == expected, "Row count expected = {0}, while actual row count = {1}".format(expected, actual)

    @pytest.mark.asyncio
    async def test_csv_ingest_existing_table(self):
        csv_ingest_props = IngestionProperties(
            self.test_db,
            self.test_table,
            data_format=DataFormat.CSV,
            ingestion_mapping=self.get_test_table_csv_mappings(),
            report_level=ReportLevel.FailuresAndSuccesses,
            flush_immediately=True,
        )

        for f in [self.csv_file_path, self.zipped_csv_file_path]:
            self.ingest_client.ingest_from_file(f, csv_ingest_props)

        await self.assert_rows_added(20)

    @pytest.mark.asyncio
    async def test_json_ingest_existing_table(self):
        json_ingestion_props = IngestionProperties(
            self.test_db,
            self.test_table,
            flush_immediately=True,
            data_format=DataFormat.JSON,
            ingestion_mapping=self.test_table_json_mappings(),
            report_level=ReportLevel.FailuresAndSuccesses,
        )

        for f in [self.json_file_path, self.zipped_json_file_path]:
            self.ingest_client.ingest_from_file(f, json_ingestion_props)

        await self.assert_rows_added(4)

    @pytest.mark.asyncio
    async def test_ingest_complicated_props(self):
        validation_policy = ValidationPolicy(
            validation_options=ValidationOptions.ValidateCsvInputConstantColumns, validation_implications=ValidationImplications.Fail
        )
        json_ingestion_props = IngestionProperties(
            self.test_db,
            self.test_table,
            data_format=DataFormat.JSON,
            ingestion_mapping=self.test_table_json_mappings(),
            additional_tags=["a", "b"],
            ingest_if_not_exists=["aaaa", "bbbb"],
            ingest_by_tags=["ingestByTag"],
            drop_by_tags=["drop", "drop-by"],
            flush_immediately=False,
            report_level=ReportLevel.FailuresAndSuccesses,
            report_method=ReportMethod.Queue,
            validation_policy=validation_policy,
        )

        file_paths = [self.json_file_path, self.zipped_json_file_path]
        fds = [FileDescriptor(fp, 0, uuid.uuid4()) for fp in file_paths]

        for fd in fds:
            self.ingest_client.ingest_from_file(fd, json_ingestion_props)

        await self.assert_rows_added(4)

    @pytest.mark.asyncio
    async def test_json_ingestion_ingest_by_tag(self):
        json_ingestion_props = IngestionProperties(
            self.test_db,
            self.test_table,
            data_format=DataFormat.JSON,
            ingestion_mapping=self.test_table_json_mappings(),
            ingest_if_not_exists=["ingestByTag"],
            report_level=ReportLevel.FailuresAndSuccesses,
            drop_by_tags=["drop", "drop-by"],
            flush_immediately=True,
        )

        for f in [self.json_file_path, self.zipped_json_file_path]:
            self.ingest_client.ingest_from_file(f, json_ingestion_props)

        await self.assert_rows_added(0)

    @pytest.mark.asyncio
    async def test_tsv_ingestion_csv_mapping(self):
        tsv_ingestion_props = IngestionProperties(
            self.test_db,
            self.test_table,
            flush_immediately=True,
            data_format=DataFormat.TSV,
            ingestion_mapping=self.get_test_table_csv_mappings(),
            report_level=ReportLevel.FailuresAndSuccesses,
        )

        self.ingest_client.ingest_from_file(self.tsv_file_path, tsv_ingestion_props)

        await self.assert_rows_added(10)

    @pytest.mark.asyncio
    async def test_streaming_ingest_from_opened_file(self):
        self.client.execute(self.test_db, CLEAR_DB_CACHE)
        ingestion_properties = IngestionProperties(database=self.test_db, table=self.test_table, data_format=DataFormat.CSV)

        with open(self.csv_file_path, "r") as stream:
            self.streaming_ingest_client.ingest_from_stream(stream, ingestion_properties=ingestion_properties)

        await self.assert_rows_added(10, timeout=120)

    @pytest.mark.asyncio
    async def test_streaming_ingest_from_csv_file(self):
        self.client.execute(self.test_db, CLEAR_DB_CACHE)
        ingestion_properties = IngestionProperties(database=self.test_db, table=self.test_table, flush_immediately=True, data_format=DataFormat.CSV)

        for f in [self.csv_file_path, self.zipped_csv_file_path]:
            self.streaming_ingest_client.ingest_from_file(f, ingestion_properties=ingestion_properties)

        await self.assert_rows_added(20, timeout=120)

    @pytest.mark.asyncio
    async def test_streaming_ingest_from_json_file(self):
        self.client.execute(self.test_db, CLEAR_DB_CACHE)
        ingestion_properties = IngestionProperties(
            database=self.test_db,
            table=self.test_table,
            flush_immediately=True,
            data_format=DataFormat.JSON,
            ingestion_mapping_reference="JsonMapping",
            ingestion_mapping_type=IngestionMappingType.JSON,
        )

        for f in [self.json_file_path, self.zipped_json_file_path]:
            self.streaming_ingest_client.ingest_from_file(f, ingestion_properties=ingestion_properties)

        await self.assert_rows_added(4, timeout=120)

    @pytest.mark.asyncio
    async def test_streaming_ingest_from_csv_io_streams(self):
        self.client.execute(self.test_db, CLEAR_DB_CACHE)
        ingestion_properties = IngestionProperties(database=self.test_db, table=self.test_table, data_format=DataFormat.CSV)
        byte_sequence = b'0,00000000-0000-0000-0001-020304050607,0,0,0,0,0,0,0,0,0,0,2014-01-01T01:01:01.0000000Z,Zero,"Zero",0,00:00:00,,null'
        bytes_stream = io.BytesIO(byte_sequence)
        self.streaming_ingest_client.ingest_from_stream(bytes_stream, ingestion_properties=ingestion_properties)

        str_sequence = '0,00000000-0000-0000-0001-020304050607,0,0,0,0,0,0,0,0,0,0,2014-01-01T01:01:01.0000000Z,Zero,"Zero",0,00:00:00,,null'
        str_stream = io.StringIO(str_sequence)
        self.streaming_ingest_client.ingest_from_stream(str_stream, ingestion_properties=ingestion_properties)

        await self.assert_rows_added(2, timeout=120)

    @pytest.mark.asyncio
    async def test_streaming_ingest_from_json_io_streams(self):
        ingestion_properties = IngestionProperties(
            database=self.test_db,
            table=self.test_table,
            data_format=DataFormat.JSON,
            flush_immediately=True,
            ingestion_mapping_reference="JsonMapping",
            ingestion_mapping_type=IngestionMappingType.JSON,
        )

        byte_sequence = b'{"rownumber": 0, "rowguid": "00000000-0000-0000-0001-020304050607", "xdouble": 0.0, "xfloat": 0.0, "xbool": 0, "xint16": 0, "xint32": 0, "xint64": 0, "xunit8": 0, "xuint16": 0, "xunit32": 0, "xunit64": 0, "xdate": "2014-01-01T01:01:01Z", "xsmalltext": "Zero", "xtext": "Zero", "xnumberAsText": "0", "xtime": "00:00:00", "xtextWithNulls": null, "xdynamicWithNulls": ""}'
        bytes_stream = io.BytesIO(byte_sequence)
        self.streaming_ingest_client.ingest_from_stream(bytes_stream, ingestion_properties=ingestion_properties)

        str_sequence = '{"rownumber": 0, "rowguid": "00000000-0000-0000-0001-020304050607", "xdouble": 0.0, "xfloat": 0.0, "xbool": 0, "xint16": 0, "xint32": 0, "xint64": 0, "xunit8": 0, "xuint16": 0, "xunit32": 0, "xunit64": 0, "xdate": "2014-01-01T01:01:01Z", "xsmalltext": "Zero", "xtext": "Zero", "xnumberAsText": "0", "xtime": "00:00:00", "xtextWithNulls": null, "xdynamicWithNulls": ""}'
        str_stream = io.StringIO(str_sequence)
        self.streaming_ingest_client.ingest_from_stream(str_stream, ingestion_properties=ingestion_properties)

        await self.assert_rows_added(2, timeout=120)

    @pytest.mark.asyncio
    async def test_streaming_ingest_from_dataframe(self):
        from pandas import DataFrame

        fields = [
            "rownumber",
            "rowguid",
            "xdouble",
            "xfloat",
            "xbool",
            "xint16",
            "xint32",
            "xint64",
            "xunit8",
            "xuint16",
            "xunit32",
            "xunit64",
            "xdate",
            "xsmalltext",
            "xtext",
            "xnumberAsText",
            "xtime",
            "xtextWithNulls",
            "xdynamicWithNulls",
        ]
        rows = [
            [0, "00000000-0000-0000-0001-020304050607", 0.0, 0.0, 0, 0, 0, 0, 0, 0, 0, 0, "2014-01-01T01:01:01Z", "Zero", "Zero", "0", "00:00:00", None, ""]
        ]
        df = DataFrame(data=rows, columns=fields)
        ingestion_properties = IngestionProperties(database=self.test_db, table=self.test_table, flush_immediately=True, data_format=DataFormat.CSV)
        self.ingest_client.ingest_from_dataframe(df, ingestion_properties)

        await self.assert_rows_added(1, timeout=120)

    def test_cloud_info(self):
        cloud_info = CloudSettings.get_cloud_info_for_cluster(self.engine_cs)
        assert cloud_info is not CloudSettings.DEFAULT_CLOUD
        assert cloud_info == CloudSettings.DEFAULT_CLOUD
        assert cloud_info is CloudSettings.get_cloud_info_for_cluster(self.engine_cs)

    def test_cloud_info_404(self):
        cloud_info = CloudSettings.get_cloud_info_for_cluster("https://www.microsoft.com")
        assert cloud_info is CloudSettings.DEFAULT_CLOUD
