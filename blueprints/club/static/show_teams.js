// club/static/show_teams.js

// Fonction pour supprimer une équipe du club
function confirmDelete(teamId) {
    var result = confirm("Êtes-vous sûr de vouloir supprimer cette équipe?");
    if (result) {
        window.location.href = "delete_team/" + teamId;
    }
}
// Fonction pour afficher ou masquer l'info-bulle
function toggleTooltip(element) {
    // Récupérer l'élément de l'info-bulle
    var tooltip = element.querySelector('.tooltiptext');

    // Vérifier si l'appareil est un smartphone (largeur d'écran inférieure à 768px)
    var isMobile = window.innerWidth < 768;

    // Si c'est un smartphone, basculer l'affichage de l'info-bulle sur clic
    if (isMobile) {
        // Vérifier si l'info-bulle est déjà affichée
        var isVisible = tooltip.classList.contains('show');

        // Si l'info-bulle est déjà affichée, la cacher
        if (isVisible) {
            tooltip.classList.remove('show');
        } else {
            // Sinon, afficher l'info-bulle et masquer après 3 secondes
            tooltip.classList.add('show');
            setTimeout(function() {
                tooltip.classList.remove('show');
            }, 3000); // 3000 ms = 3 secondes
        }
    } else {
        // Si ce n'est pas un smartphone, basculer l'affichage de l'info-bulle sur survol
        tooltip.classList.toggle('show');
    }
}
