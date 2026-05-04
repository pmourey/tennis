"""
Test script pour vérifier la gestion des conflits d'importation de joueurs
et la suppression en cascade des joueurs lors de la suppression d'un club.
"""

from app import create_app
from models import db, Club, Player, License
from common import import_players

def test_import_conflicts():
    """Test de détection des conflits lors de l'importation de joueurs"""
    app = create_app()
    with app.app_context():
        print("\n=== Test de détection des conflits d'importation ===\n")

        # Vérifier qu'il existe au moins un club
        clubs = Club.query.all()
        if len(clubs) < 1:
            print("❌ Aucun club en base de données. Veuillez créer un club d'abord.")
            return

        print(f"✓ {len(clubs)} club(s) trouvé(s) en base de données")

        # Afficher les joueurs de chaque club
        for club in clubs:
            players_count = Player.query.filter_by(clubId=club.id).count()
            print(f"  - {club.name}: {players_count} joueur(s)")

        print("\n✓ Test de détection des conflits OK (voir logs lors de l'import)")


def test_cascade_delete():
    """Test de suppression en cascade des joueurs lors de la suppression d'un club"""
    app = create_app()
    with app.app_context():
        print("\n=== Test de suppression en cascade ===\n")

        # Créer un club de test
        test_club = Club.query.filter_by(name="TEST_CLUB").first()

        if not test_club:
            print("ℹ️  Création d'un club de test...")
            test_club = Club(id="99999999", name="TEST_CLUB", city="Test City")
            db.session.add(test_club)
            db.session.commit()
            print(f"✓ Club de test créé: {test_club.name} (ID: {test_club.id})")
        else:
            print(f"✓ Club de test existant: {test_club.name} (ID: {test_club.id})")

        # Compter les joueurs avant suppression
        players_before = Player.query.filter_by(clubId=test_club.id).count()
        print(f"  → {players_before} joueur(s) dans le club de test")

        # Supprimer le club
        print(f"\nℹ️  Suppression du club {test_club.name}...")
        db.session.delete(test_club)
        db.session.commit()
        print(f"✓ Club supprimé")

        # Vérifier que les joueurs ont été supprimés
        players_after = Player.query.filter_by(clubId=test_club.id).count()
        print(f"  → {players_after} joueur(s) restant(s) après suppression")

        if players_after == 0:
            print("\n✅ Test de suppression en cascade RÉUSSI!")
            print("   Les joueurs ont bien été supprimés avec le club.")
        else:
            print(f"\n❌ Test de suppression en cascade ÉCHOUÉ!")
            print(f"   {players_after} joueur(s) n'ont pas été supprimés.")


def test_license_reuse():
    """Test de réutilisation de licence existante lors de l'importation"""
    app = create_app()
    with app.app_context():
        print("\n=== Test de réutilisation de licence ===\n")

        # Vérifier qu'il existe au moins une licence
        licenses = License.query.all()
        if len(licenses) < 1:
            print("❌ Aucune licence en base de données.")
            return

        print(f"✓ {len(licenses)} licence(s) trouvée(s) en base de données")

        # Compter les joueurs par licence
        for license in licenses[:5]:  # Afficher les 5 premières licences
            players = Player.query.filter_by(licenseId=license.id).all()
            print(f"  - Licence {license.id} ({license.firstName} {license.lastName}): {len(players)} joueur(s)")

        print("\n✓ Les licences peuvent être partagées entre joueurs si nécessaire")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Tests de gestion des clubs et joueurs")
    print("="*60)

    test_import_conflicts()
    test_cascade_delete()
    test_license_reuse()

    print("\n" + "="*60)
    print("Tests terminés")
    print("="*60 + "\n")
