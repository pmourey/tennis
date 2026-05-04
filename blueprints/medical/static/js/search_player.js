$(document).ready(function() {
    $('#search-form').submit(function(event) {
        event.preventDefault();
        var formData = $(this).serialize();
        $.ajax({
            type: 'GET',
            url: '{{ url_for("medical.search_players") }}',
            data: formData,
            success: function(response) {
                $('#search-results').html(response);
            },
            error: function(xhr, status, error) {
                console.error('Error:', error);
            }
        });
    });
});