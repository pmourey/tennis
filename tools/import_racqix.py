"""Import des raquettes et cordages depuis l'API Racqix vers la base de données."""
import json
import ssl
import sys
import os
import subprocess
import urllib.request

# Désactiver la vérification SSL (certificat auto-signé sur macOS)
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

NEUTRAL_MM = 685.8 / 2  # 342.9 mm


def balance_pts(balance_mm_from_handle):
    """Convertit mm depuis le manche en points (convention DB: négatif=HL, positif=HH)."""
    if balance_mm_from_handle is None:
        return None
    balance_from_head = 685.8 - balance_mm_from_handle
    pts = (NEUTRAL_MM - balance_from_head) / 3.175
    return round(pts, 1)


def _fetch_json(url):
    """Fetch JSON via curl pour contourner les restrictions User-Agent."""
    result = subprocess.run(
        ["curl", "-s", "--max-time", "30", url],
        capture_output=True, text=True
    )
    return json.loads(result.stdout)


def import_racquets(app):
    print("Fetching racquets from racqix…")
    data = _fetch_json("https://www.racqix.com/api/racquet-finder")
    racquets = data["racquets"]
    print(f"  {len(racquets)} raquettes reçues")

    from blueprints.shop.models import Racquet
    from extensions import db

    created = updated = 0
    for rq in racquets:
        rid = rq["id"]
        brand = rq.get("brand", "")
        model = rq.get("model", "")
        year = rq.get("year", "")
        head = rq.get("specsHeadSizeIn")
        weight = rq.get("specsWeightUnstrungG")
        pattern = rq.get("specsStringPattern", "")

        name_parts = [model, year]
        if head:
            name_parts.append(f'{head}"')
        if weight:
            name_parts.append(f"{weight}g")
        name = " ".join(p for p in name_parts if p)

        bal = balance_pts(rq.get("specsBalanceUnstrungMm"))
        pl = rq.get("recommendationsPlayerLevel") or []

        existing = Racquet.query.filter_by(racqix_id=rid).first()
        if existing is None:
            existing = Racquet.query.filter_by(brand=brand, name=name).first()

        if existing is None:
            existing = Racquet(brand=brand, name=name)
            db.session.add(existing)
            created += 1
        else:
            updated += 1

        existing.racqix_id = rid
        existing.racqix_slug = rq.get("slug")
        existing.head_size = head
        existing.unstrung_weight = weight
        if bal is not None:
            existing.balance = bal
        if rq.get("specsStiffnessRa"):
            existing.stiffness = rq["specsStiffnessRa"]
        if pattern:
            existing.string_pattern = pattern
        existing.image_url = rq.get("mediaImageUrl")
        if year:
            try:
                existing.release_year = int(year)
            except (ValueError, TypeError):
                pass
        existing.is_current = True
        existing.scores_power = rq.get("scoresPower")
        existing.scores_control = rq.get("scoresControl")
        existing.scores_spin = rq.get("scoresSpin")
        existing.category_tag = rq.get("recommendationsCategoryTag")
        existing.player_level = ",".join(pl) if pl else None
        existing.swing_style = rq.get("recommendationsSwingStyle")
        existing.play_style = rq.get("recommendationsPlayStyleFit")

    db.session.commit()
    print(f"  Raquettes: {created} créées, {updated} mises à jour")


def import_strings(app):
    print("Fetching strings from racqix…")
    sdata = _fetch_json("https://www.racqix.com/api/string-finder")
    strings = sdata.get("strings", [])
    print(f"  {len(strings)} cordages reçus")

    from blueprints.shop.models import RacqixString
    from extensions import db

    sc = su = 0
    for s in strings:
        slug = s.get("slug", "")
        if not slug:
            continue
        ratings = s.get("ratings") or {}
        gauges_json = json.dumps(s.get("gauges", []))

        existing = RacqixString.query.filter_by(slug=slug).first()
        if existing is None:
            existing = RacqixString(slug=slug)
            db.session.add(existing)
            sc += 1
        else:
            su += 1

        existing.brand = s.get("brand", "")
        existing.name = s.get("name", "")
        existing.family = s.get("family")
        existing.shape = s.get("shape")
        existing.string_type = s.get("string_type")
        existing.gauges_json = gauges_json
        existing.rating_comfort = ratings.get("comfort")
        existing.rating_control = ratings.get("control")
        existing.rating_power = ratings.get("power")
        existing.rating_spin = ratings.get("spin")
        existing.image_url = s.get("image_pathway_string")

    db.session.commit()
    print(f"  Cordages: {sc} créés, {su} mis à jour")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        import_racquets(app)
        import_strings(app)
    print("Import terminé.")







