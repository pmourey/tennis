"""
Script de migration pour ajouter un meilleur classement aux licences qui n'en ont pas.
Pour les licences sans bestRankingId, on utilise le rankingId comme valeur par défaut.
"""

from app import create_app
from models import db, License

def migrate_best_rankings():
    """
    Met à jour toutes les licences sans meilleur classement
    en utilisant le classement actuel comme meilleur classement par défaut.
    """
    app = create_app()
    with app.app_context():
        print("\n" + "="*60)
        print("Migration : Ajout du meilleur classement aux licences")
        print("="*60 + "\n")

        # Trouver toutes les licences sans meilleur classement
        licenses_without_best = License.query.filter(License.bestRankingId == None).all()

        if not licenses_without_best:
            print("✅ Aucune licence à migrer. Toutes les licences ont déjà un meilleur classement.")
            return

        print(f"📋 {len(licenses_without_best)} licence(s) trouvée(s) sans meilleur classement\n")

        # Afficher quelques exemples avant migration
        print("Exemples de licences à migrer :")
        for license in licenses_without_best[:5]:
            print(f"  - Licence {license.id} : {license.firstName} {license.lastName}")
            print(f"    Classement actuel : {license.ranking.value}")
            print(f"    Meilleur classement : None → {license.ranking.value}")

        if len(licenses_without_best) > 5:
            print(f"  ... et {len(licenses_without_best) - 5} autre(s)")

        print("\n" + "-"*60)

        # Demander confirmation
        response = input(f"\n⚠️  Voulez-vous migrer ces {len(licenses_without_best)} licence(s) ? (oui/non) : ")

        if response.lower() not in ['oui', 'o', 'yes', 'y']:
            print("\n❌ Migration annulée par l'utilisateur.")
            return

        print("\n🔄 Migration en cours...")

        # Effectuer la migration
        migrated_count = 0
        for license in licenses_without_best:
            try:
                license.bestRankingId = license.rankingId
                migrated_count += 1
            except Exception as e:
                print(f"❌ Erreur pour la licence {license.id}: {e}")

        # Commit des changements
        try:
            db.session.commit()
            print(f"\n✅ Migration réussie : {migrated_count} licence(s) mise(s) à jour")
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Erreur lors du commit : {e}")
            return

        # Vérification
        print("\n" + "-"*60)
        print("Vérification...")
        remaining = License.query.filter(License.bestRankingId == None).count()

        if remaining == 0:
            print("✅ Toutes les licences ont maintenant un meilleur classement")
        else:
            print(f"⚠️  Il reste {remaining} licence(s) sans meilleur classement")

        print("\n" + "="*60)
        print("Migration terminée")
        print("="*60 + "\n")


def verify_best_rankings():
    """
    Vérifie l'état des meilleurs classements dans la base de données.
    """
    app = create_app()
    with app.app_context():
        print("\n" + "="*60)
        print("Vérification des meilleurs classements")
        print("="*60 + "\n")

        total_licenses = License.query.count()
        licenses_with_best = License.query.filter(License.bestRankingId != None).count()
        licenses_without_best = total_licenses - licenses_with_best

        print(f"Total de licences : {total_licenses}")
        print(f"  ✅ Avec meilleur classement : {licenses_with_best}")
        print(f"  ❌ Sans meilleur classement : {licenses_without_best}")

        if licenses_without_best > 0:
            print(f"\n⚠️  {licenses_without_best} licence(s) nécessite(nt) une migration")
            print("   Exécutez la fonction migrate_best_rankings() pour corriger cela.")
        else:
            print("\n✅ Tous les joueurs ont un meilleur classement défini !")

        print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--verify':
        verify_best_rankings()
    else:
        migrate_best_rankings()
