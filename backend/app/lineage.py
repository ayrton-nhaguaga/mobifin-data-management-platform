from app.models import LineageNode, LineageEdge


def node(db, batch, key, name, kind, description, status='SUCCESS'):
    item = LineageNode(id=key, batch_id=batch.id, name=name, kind=kind, description=description, status=status)
    db.add(item)
    db.flush()
    return item


def edge(db, source, target, description):
    db.add(LineageEdge(source=source, target=target, description=description))
