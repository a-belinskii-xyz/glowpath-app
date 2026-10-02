from app.services.storage import STREAM_CHUNK_SIZE, MinioStorage


class _FakeResponse:
    def __init__(self, data: bytes) -> None:
        self._data = data
        self.closed = False
        self.released = False

    def stream(self, amt: int):
        for i in range(0, len(self._data), amt):
            yield self._data[i : i + amt]

    def close(self) -> None:
        self.closed = True

    def release_conn(self) -> None:
        self.released = True


class _FakeClient:
    def __init__(self, response: _FakeResponse) -> None:
        self.response = response

    def get_object(self, bucket: str, key: str) -> _FakeResponse:
        return self.response


def _storage(data: bytes) -> tuple[MinioStorage, _FakeResponse]:
    storage = MinioStorage(endpoint="localhost:9000", access_key="a", secret_key="b", bucket="t")
    response = _FakeResponse(data)
    storage._client = _FakeClient(response)  # type: ignore[assignment]
    storage._bucket_ready = True
    return storage, response


def test_stream_object_yields_chunks_and_releases_connection() -> None:
    data = b"x" * (STREAM_CHUNK_SIZE * 2 + 10)
    storage, response = _storage(data)

    chunks = list(storage.stream_object(key="k"))

    assert b"".join(chunks) == data
    assert max(len(chunk) for chunk in chunks) == STREAM_CHUNK_SIZE
    assert response.closed and response.released


def test_stream_object_releases_connection_when_client_disconnects() -> None:
    storage, response = _storage(b"x" * (STREAM_CHUNK_SIZE * 3))

    chunks = storage.stream_object(key="k")
    next(chunks)
    chunks.close()  # type: ignore[attr-defined]

    assert response.closed and response.released
