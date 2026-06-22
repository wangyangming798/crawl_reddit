from crawler.base import RawPost, RawComment


def dedup_posts(posts: list[RawPost]) -> list[RawPost]:
    """Remove duplicate posts by post_id, keeping first occurrence."""
    seen: set[str] = set()
    result: list[RawPost] = []
    for post in posts:
        if post.post_id not in seen:
            seen.add(post.post_id)
            result.append(post)
    return result


def dedup_comments(comments: list[RawComment]) -> list[RawComment]:
    """Remove duplicate comments by comment_id, keeping first occurrence."""
    seen: set[str] = set()
    result: list[RawComment] = []
    for comment in comments:
        if comment.comment_id not in seen:
            seen.add(comment.comment_id)
            result.append(comment)
    return result