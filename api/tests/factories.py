from itertools import count

from empu.enums import AccessLevel, ContributorRole
from empu.models import Archive, Contributor, Recording

_n = count(1)


def _save(session, obj):
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


def make_archive(session, **kw) -> Archive:
    n = next(_n)
    return _save(
        session,
        Archive(
            **({"slug": f"arsip-{n}", "title": f"Arsip {n}", "craft_pack_id": "batik_tulis"} | kw)
        ),
    )


def make_contributor(session, **kw) -> Contributor:
    defaults = {"name": f"Ahli {next(_n)}", "role": ContributorRole.maestro}
    return _save(session, Contributor(**(defaults | kw)))


def make_recording(session, archive, **kw) -> Recording:
    return _save(
        session,
        Recording(
            **(
                {
                    "archive_id": archive.id,
                    "title": "Rekaman uji",
                    "original_path": "",
                    "consent_scope": AccessLevel.public,
                }
                | kw
            )
        ),
    )
