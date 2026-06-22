from pipeline.dedup import dedup_posts, dedup_comments
from crawler.base import RawPost, RawComment


def test_dedup_posts_no_duplicates():
    posts = [
        RawPost(post_id="p1", title="T1", body="", author_id="a1", created_at=1.0, sub_community="r/test", raw_json={}),
        RawPost(post_id="p2", title="T2", body="", author_id="a2", created_at=2.0, sub_community="r/test", raw_json={}),
    ]
    result = dedup_posts(posts)
    assert len(result) == 2


def test_dedup_posts_removes_duplicates():
    posts = [
        RawPost(post_id="p1", title="T1", body="", author_id="a1", created_at=1.0, sub_community="r/test", raw_json={}),
        RawPost(post_id="p1", title="T1 dup", body="", author_id="a1", created_at=2.0, sub_community="r/test", raw_json={}),
        RawPost(post_id="p2", title="T2", body="", author_id="a2", created_at=3.0, sub_community="r/test", raw_json={}),
    ]
    result = dedup_posts(posts)
    assert len(result) == 2
    # First occurrence kept
    assert result[0].title == "T1"


def test_dedup_posts_empty():
    assert dedup_posts([]) == []


def test_dedup_comments_removes_duplicates():
    comments = [
        RawComment(comment_id="c1", post_id="p1", body="B1", author_id="a1", created_at=1.0, raw_json={}),
        RawComment(comment_id="c1", post_id="p1", body="B1 dup", author_id="a1", created_at=2.0, raw_json={}),
        RawComment(comment_id="c2", post_id="p1", body="B2", author_id="a2", created_at=3.0, raw_json={}),
    ]
    result = dedup_comments(comments)
    assert len(result) == 2