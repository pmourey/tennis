import time
from app import create_app
from blueprints.shop.models import Racquet
from extensions import db


def main():
    app = create_app()

    with app.app_context():
        before_total = db.session.query(Racquet).count()
        before_head = db.session.query(Racquet).filter(Racquet.head_size.isnot(None)).count()
        print(f"DB before: total={before_total}, head_size_not_null={before_head}")

    start = time.time()

    with app.test_client() as client:
        response = client.post(
            '/shop/scrape',
            data={
                'manufacturer': '',
                'normalize_legacy': 'on',
            },
            follow_redirects=True,
        )
        html = response.data.decode('utf-8', errors='ignore')
        ok_msg = ('Import termine' in html) or ('Import terminé' in html)
        err_msg = 'Erreur pendant le scraping' in html
        print(f"HTTP status={response.status_code}, success_flash={ok_msg}, error_flash={err_msg}")

    with app.app_context():
        after_total = db.session.query(Racquet).count()
        after_head = db.session.query(Racquet).filter(Racquet.head_size.isnot(None)).count()
        low_weight = db.session.query(Racquet).filter(
            Racquet.strung_weight.isnot(None),
            Racquet.strung_weight <= 30,
        ).count()
        min_weight = db.session.query(db.func.min(Racquet.strung_weight)).scalar()
        max_weight = db.session.query(db.func.max(Racquet.strung_weight)).scalar()
        print(f"DB after: total={after_total}, head_size_not_null={after_head}")
        print(f"Weight check: <=30g_count={low_weight}, min={min_weight}, max={max_weight}")

    print(f"Elapsed: {time.time() - start:.1f}s")


if __name__ == '__main__':
    main()

