// club/static/manage_player.js

// Fonction pour supprimer un joueur du club
    function confirmDelete(deleteUrl) {
        var result = confirm("Êtes-vous sûr de vouloir supprimer ce joueur?");
        if (result) {
            window.location.href = deleteUrl;
        }
    }