(function () {
    "use strict";

    function filterMatches(teamSelect, matchSelect, url) {
        const teamId = teamSelect.value;
        const currentValue = matchSelect.value;

        if (!teamId) {
            matchSelect.innerHTML = '<option value="">---------</option>';
            return;
        }

        fetch(`${url}?team_id=${encodeURIComponent(teamId)}`, {
            headers: { "X-Requested-With": "XMLHttpRequest" },
        })
            .then((response) => response.json())
            .then((matches) => {
                matchSelect.innerHTML = "";
                const emptyOption = document.createElement("option");
                emptyOption.value = "";
                emptyOption.textContent = "---------";
                matchSelect.appendChild(emptyOption);

                matches.forEach((match) => {
                    const option = document.createElement("option");
                    option.value = match.id;
                    option.textContent = match.label;
                    matchSelect.appendChild(option);
                });

                if ([...matchSelect.options].some((option) => option.value === currentValue)) {
                    matchSelect.value = currentValue;
                }
            });
    }

    document.addEventListener("DOMContentLoaded", function () {
        const teamSelect = document.getElementById("id_team");
        const matchSelect = document.getElementById("id_match");

        if (!teamSelect || !matchSelect) {
            return;
        }

        const url = matchSelect.dataset.filterUrl;
        if (!url) {
            return;
        }

        teamSelect.addEventListener("change", function () {
            filterMatches(teamSelect, matchSelect, url);
        });
    });
})();
