"""
Tests unitaires pour la logique de saisie et validation des scores de tennis.
Couvre :
  - parsePart()      : parsing d'une partie du score "7/6(4)" → [7, 6, 4]
  - isValidSet()     : validation d'un score de set classique
  - isTBSet()        : détection d'un set avec tie-break (7-6 ou 6-7)
  - tbWinScore()     : calcul du score gagnant au TB (max(7, loser+2))
  - isValidSuperTB() : validation d'un super tie-break (≥10 pts, écart ≥2)
  - buildScoreText() : construction du texte de score complet
  - getTBLoser()     : extraction du score du perdant au TB
"""
import re
import pytest


# ─── Implémentation Python des fonctions JS pour les tests ──────────────────

VALID_SETS = [
    (6,0),(6,1),(6,2),(6,3),(6,4),(7,5),(7,6),
    (0,6),(1,6),(2,6),(3,6),(4,6),(5,7),(6,7)
]

def is_valid_set(a, b):
    return (a, b) in VALID_SETS

def is_valid_super_tb(a, b):
    return max(a, b) >= 10 and abs(a - b) >= 2

def is_tb_set(a, b):
    return (a == 7 and b == 6) or (a == 6 and b == 7)

def tb_win_score(loser):
    """Score du gagnant au TB = max(7, loser + 2)"""
    if loser is None:
        return 7
    return max(7, loser + 2)

def parse_part(p):
    """
    Parse une partie de score texte.
    "7/6(4)" → (7, 6, 4)   # (sa, sb, tb_loser)
    "6/0"    → (6, 0, None)
    ""       → (None, None, None)
    """
    if not p or not p.strip():
        return (None, None, None)
    tb_match = re.search(r'\((\d+)\)', p)
    tb = int(tb_match.group(1)) if tb_match else None
    clean = re.sub(r'\(\d+\)', '', p).strip()
    parts = clean.split('/')
    try:
        a = int(parts[0])
    except (ValueError, IndexError):
        a = None
    try:
        b = int(parts[1])
    except (ValueError, IndexError):
        b = None
    return (a, b, tb)

def get_tb_loser(sa, sb, val_a, val_b):
    """
    Retourne le score du perdant au TB.
    val_a : score côté P1 (None si P1 a gagné le set)
    val_b : score côté P2 (None si P2 a gagné le set)
    """
    if not is_tb_set(sa, sb):
        return None
    return val_b if sa > sb else val_a

def set_str(sa, sb, tb_loser=None):
    """Construit la partie texte d'un set, ex: "7/6(4)", "6/3"."""
    s = f"{sa}/{sb}"
    if is_tb_set(sa, sb) and tb_loser is not None:
        s += f"({tb_loser})"
    return s

def build_score_text(sets, fmt=1):
    """
    Construit le texte de score complet.
    sets : liste de (sa, sb, tb_loser) pour chaque set
    fmt  : 1 = 3 sets / 2 = 2 sets + super TB
    """
    return ' '.join(set_str(sa, sb, tb) for sa, sb, tb in sets)


# ─── Tests parse_part ────────────────────────────────────────────────────────

class TestParsePart:
    def test_simple_score(self):
        assert parse_part("6/3") == (6, 3, None)

    def test_score_with_zero(self):
        """Bug corrigé : 6/0 ne doit pas être traité comme None."""
        a, b, tb = parse_part("6/0")
        assert a == 6
        assert b == 0  # 0 est une valeur valide !
        assert tb is None

    def test_zero_slash_six(self):
        a, b, tb = parse_part("0/6")
        assert a == 0
        assert b == 6

    def test_tb_set(self):
        a, b, tb = parse_part("7/6(4)")
        assert a == 7
        assert b == 6
        assert tb == 4

    def test_tb_set_p2_wins(self):
        a, b, tb = parse_part("6/7(3)")
        assert a == 6
        assert b == 7
        assert tb == 3

    def test_tb_loser_zero(self):
        """Le perdant peut avoir 0 points au TB."""
        a, b, tb = parse_part("7/6(0)")
        assert tb == 0

    def test_super_tb(self):
        a, b, tb = parse_part("10/7")
        assert a == 10
        assert b == 7
        assert tb is None

    def test_empty_string(self):
        assert parse_part("") == (None, None, None)

    def test_none_input(self):
        assert parse_part(None) == (None, None, None)


# ─── Tests is_valid_set ──────────────────────────────────────────────────────

class TestIsValidSet:
    @pytest.mark.parametrize("a,b", [
        (6,0),(6,1),(6,2),(6,3),(6,4),(7,5),(7,6),
        (0,6),(1,6),(2,6),(3,6),(4,6),(5,7),(6,7),
    ])
    def test_valid_scores(self, a, b):
        assert is_valid_set(a, b), f"{a}/{b} devrait être valide"

    @pytest.mark.parametrize("a,b", [
        (5,5),(6,6),(7,7),(8,5),(5,8),(3,3),(6,5),(5,6),
    ])
    def test_invalid_scores(self, a, b):
        assert not is_valid_set(a, b), f"{a}/{b} ne devrait pas être valide"

    def test_six_zero_is_valid(self):
        """Bug principal : 6/0 DOIT être valide."""
        assert is_valid_set(6, 0)
        assert is_valid_set(0, 6)


# ─── Tests is_tb_set ─────────────────────────────────────────────────────────

class TestIsTBSet:
    def test_p1_wins_tb(self):
        assert is_tb_set(7, 6)

    def test_p2_wins_tb(self):
        assert is_tb_set(6, 7)

    def test_not_tb(self):
        assert not is_tb_set(6, 3)
        assert not is_tb_set(7, 5)
        assert not is_tb_set(6, 0)


# ─── Tests tb_win_score ──────────────────────────────────────────────────────

class TestTbWinScore:
    def test_loser_4(self):
        assert tb_win_score(4) == 7

    def test_loser_5(self):
        assert tb_win_score(5) == 7

    def test_loser_6(self):
        assert tb_win_score(6) == 8

    def test_loser_0(self):
        assert tb_win_score(0) == 7

    def test_loser_none(self):
        assert tb_win_score(None) == 7

    def test_loser_large(self):
        assert tb_win_score(10) == 12


# ─── Tests is_valid_super_tb ─────────────────────────────────────────────────

class TestIsValidSuperTB:
    @pytest.mark.parametrize("a,b", [
        (10,7),(10,8),(12,10),(11,9),(10,4),
    ])
    def test_valid_super_tb(self, a, b):
        assert is_valid_super_tb(a, b)
        assert is_valid_super_tb(b, a)  # symétrique

    @pytest.mark.parametrize("a,b", [
        (9,7),(7,9),(10,9),(9,10),(5,3),
    ])
    def test_invalid_super_tb(self, a, b):
        assert not is_valid_super_tb(a, b)


# ─── Tests get_tb_loser ──────────────────────────────────────────────────────

class TestGetTBLoser:
    def test_p1_wins_loser_is_b(self):
        """7/6 : P1 gagne, le perdant est P2 → loser = val_b."""
        loser = get_tb_loser(7, 6, val_a=None, val_b=4)
        assert loser == 4

    def test_p2_wins_loser_is_a(self):
        """6/7 : P2 gagne, le perdant est P1 → loser = val_a."""
        loser = get_tb_loser(6, 7, val_a=3, val_b=None)
        assert loser == 3

    def test_not_a_tb_set(self):
        assert get_tb_loser(6, 3, None, None) is None


# ─── Tests set_str ───────────────────────────────────────────────────────────

class TestSetStr:
    def test_regular_set(self):
        assert set_str(6, 3) == "6/3"

    def test_six_zero(self):
        assert set_str(6, 0) == "6/0"

    def test_tb_with_loser(self):
        assert set_str(7, 6, 4) == "7/6(4)"

    def test_tb_p2_wins(self):
        assert set_str(6, 7, 3) == "6/7(3)"

    def test_tb_loser_zero(self):
        assert set_str(7, 6, 0) == "7/6(0)"

    def test_tb_no_loser(self):
        """Sans loser_score, pas de parenthèses."""
        assert set_str(7, 6) == "7/6"


# ─── Tests build_score_text ──────────────────────────────────────────────────

class TestBuildScoreText:
    def test_two_sets_no_tb(self):
        sets = [(6,3,None),(6,4,None)]
        assert build_score_text(sets) == "6/3 6/4"

    def test_two_sets_with_tb(self):
        sets = [(6,3,None),(7,6,4)]
        assert build_score_text(sets) == "6/3 7/6(4)"

    def test_three_sets(self):
        sets = [(6,3,None),(3,6,None),(6,4,None)]
        assert build_score_text(sets) == "6/3 3/6 6/4"

    def test_three_sets_with_super_tb(self):
        sets = [(6,3,None),(3,6,None),(10,7,None)]
        assert build_score_text(sets, fmt=2) == "6/3 3/6 10/7"

    def test_score_with_zero(self):
        """6/0 doit apparaître correctement."""
        sets = [(6,0,None),(6,0,None)]
        assert build_score_text(sets) == "6/0 6/0"

    def test_tb_loser_zero(self):
        sets = [(6,0,None),(7,6,0)]
        assert build_score_text(sets) == "6/0 7/6(0)"


# ─── Tests de cohérence vainqueur/score ──────────────────────────────────────

class TestWinnerCoherence:
    def _count_sets(self, sets_scores):
        """Retourne (sets_p1, sets_p2) à partir d'une liste (a,b,tb)."""
        w1, w2 = 0, 0
        for a, b, _ in sets_scores:
            if a > b: w1 += 1
            elif b > a: w2 += 1
        return w1, w2

    def test_straight_sets_p1(self):
        sets = [(6,3,None),(6,4,None)]
        w1, w2 = self._count_sets(sets)
        assert w1 == 2 and w2 == 0

    def test_straight_sets_p2(self):
        sets = [(3,6,None),(4,6,None)]
        w1, w2 = self._count_sets(sets)
        assert w1 == 0 and w2 == 2

    def test_three_sets_p1(self):
        sets = [(6,3,None),(3,6,None),(6,4,None)]
        w1, w2 = self._count_sets(sets)
        assert w1 == 2 and w2 == 1

    def test_winner_consistency_6_0(self):
        """Vérifier que 6/0 est bien reconnu comme victoire P1."""
        sets = [(6,0,None),(6,0,None)]
        w1, w2 = self._count_sets(sets)
        assert w1 == 2 and w2 == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

