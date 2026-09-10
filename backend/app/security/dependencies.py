"""Resource dependency graph. Answers: what else breaks if this resource is damaged?"""

from __future__ import annotations

from collections import deque

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Resource, ResourceDependency


def _edges(db: Session) -> dict[int, list[int]]:
    """depends_on_id -> [dependent_id, ...] (reverse edges)."""
    graph: dict[int, list[int]] = {}
    for dep in db.scalars(select(ResourceDependency)).all():
        graph.setdefault(dep.depends_on_id, []).append(dep.dependent_id)
    return graph


def dependents_of(db: Session, resource_name: str) -> dict:
    """BFS over reverse edges: direct and transitive dependents."""
    resource = db.scalar(select(Resource).where(Resource.name == resource_name))
    if resource is None:
        return {"resource": resource_name, "direct": [], "transitive": [], "all": [], "count": 0}

    graph = _edges(db)
    names = {r.id: r.name for r in db.scalars(select(Resource)).all()}

    direct = [names[i] for i in graph.get(resource.id, [])]
    seen: set[int] = set()
    queue = deque(graph.get(resource.id, []))
    while queue:
        node = queue.popleft()
        if node in seen:
            continue
        seen.add(node)
        queue.extend(graph.get(node, []))

    all_names = sorted(names[i] for i in seen)
    transitive = sorted(n for n in all_names if n not in direct)
    return {"resource": resource_name, "direct": sorted(direct), "transitive": transitive,
            "all": all_names, "count": len(all_names)}
