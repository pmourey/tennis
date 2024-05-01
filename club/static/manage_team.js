// club/static/manage_team.js

// TODO Fonction pour créer les listes de sélection (KO)
document.addEventListener('DOMContentLoaded', function() {
    // Function to populate select element with player options
    function populatePlayerOptions(selectElement) {
        players.forEach(player => {
            const option = document.createElement('option');
            option.value = player.id;
            option.textContent = `${player.name} [${player.ranking}] (${player.age} ans)`;
            selectElement.appendChild(option);
        });
    }

    // Add event listener to each player select element
    const playerSelects = document.querySelectorAll('.player-select');
    playerSelects.forEach(select => {
        select.addEventListener('click', function() {
            populatePlayerOptions(select);
        });
    });
});

