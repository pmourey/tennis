// club/static/manage_player.js

// Fonction pour supprimer un joueur du club
    function confirmDelete(playerId) {
        var result = confirm("Êtes-vous sûr de vouloir supprimer ce joueur?");
        if (result) {
            window.location.href = "delete_player/" + playerId;
        }
    }