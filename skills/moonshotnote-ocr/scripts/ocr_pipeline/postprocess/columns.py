from __future__ import annotations

from ocr_pipeline.models import OcrItem
from ocr_pipeline.utils import normalize_box


def restore_columns(items: list[OcrItem], max_columns: int = 3) -> list[dict[str, object]]:
    positioned = []
    for item in items:
        box = normalize_box(item.box)
        if box:
            positioned.append((box[0], box[1], item.text))
    if not positioned:
        return []

    positioned.sort()
    min_x = min(x for x, _, _ in positioned)
    max_x = max(x for x, _, _ in positioned)
    width = max(1.0, max_x - min_x)
    bucket_width = max(1.0, width / max_columns)
    buckets: list[list[tuple[float, float, str]]] = [[] for _ in range(max_columns)]

    for x, y, text in positioned:
        index = min(max_columns - 1, int((x - min_x) / bucket_width))
        buckets[index].append((x, y, text))

    output = []
    for index, bucket in enumerate(buckets, start=1):
        if not bucket:
            continue
        bucket.sort(key=lambda item: (item[1], item[0]))
        output.append(
            {
                "index": index,
                "text": "\n".join(text for _, _, text in bucket if text),
                "line_count": len(bucket),
            }
        )
    return output

