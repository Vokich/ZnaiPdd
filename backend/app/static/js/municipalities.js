document.querySelectorAll('.municipality-search').forEach(function(field) {
    var input = field.querySelector('input');
    var popup = field.querySelector('.municipality-results');
    var list = field.querySelector('[role="listbox"]');
    var status = field.querySelector('[role="status"]');
    var timer;
    var request;
    var active = -1;

    input.placeholder = 'Введите регион или муниципалитет';
    input.autocomplete = 'off';
    input.setAttribute('role', 'combobox');
    input.setAttribute('aria-autocomplete', 'list');
    input.setAttribute('aria-controls', list.id);
    input.setAttribute('aria-expanded', 'false');

    function closeResults() {
        clearTimeout(timer);
        if (request) request.abort();
        list.replaceChildren();
        status.textContent = '';
        active = -1;
        popup.hidden = true;
        input.setAttribute('aria-expanded', 'false');
        input.removeAttribute('aria-activedescendant');
    }

    function select(option) {
        input.value = option.textContent;
        closeResults();
    }

    async function search(query) {
        var controller = new AbortController();
        request = controller;
        popup.hidden = false;
        status.textContent = 'Поиск…';

        try {
            var response = await fetch(field.dataset.searchUrl + '?q=' + encodeURIComponent(query), {
                signal: controller.signal
            });
            if (!response.ok) throw new Error();
            var data = await response.json();
            if (controller.signal.aborted) return;

            var options = document.createDocumentFragment();
            data.results.forEach(function(label, index) {
                var option = document.createElement('li');
                option.id = list.id + '_' + index;
                option.setAttribute('role', 'option');
                option.setAttribute('aria-selected', 'false');
                option.textContent = label;
                options.appendChild(option);
            });
            list.appendChild(options);
            input.setAttribute('aria-expanded', String(data.results.length > 0));
            status.textContent = !data.results.length ? 'Муниципалитеты не найдены' :
                data.more ? 'Показаны первые 50 результатов. Уточните запрос.' : '';
        } catch (error) {
            if (!controller.signal.aborted) {
                status.textContent = 'Не удалось загрузить список. Попробуйте ещё раз.';
            }
        } finally {
            if (request === controller) request = null;
        }
    }

    input.addEventListener('input', function() {
        closeResults();
        var query = input.value.trim();
        if (query.length >= 2) timer = setTimeout(function() { search(query); }, 180);
    });

    input.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            if (!popup.hidden) event.preventDefault();
            closeResults();
            return;
        }

        var options = list.children;
        if (!options.length) {
            if (event.key === 'ArrowDown' && input.value.trim().length >= 2 && !request) {
                event.preventDefault();
                closeResults();
                search(input.value.trim());
            }
            return;
        }

        if (event.key === 'Enter') {
            event.preventDefault();
            if (active >= 0) select(options[active]);
        } else if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
            event.preventDefault();
            if (active >= 0) options[active].setAttribute('aria-selected', 'false');
            active = event.key === 'ArrowDown' ? Math.min(active + 1, options.length - 1) :
                active < 0 ? options.length - 1 : Math.max(active - 1, 0);
            options[active].setAttribute('aria-selected', 'true');
            input.setAttribute('aria-activedescendant', options[active].id);
            options[active].scrollIntoView({block: 'nearest'});
        }
    });

    input.addEventListener('blur', closeResults);
    list.addEventListener('mousedown', function(event) { event.preventDefault(); });
    list.addEventListener('click', function(event) {
        if (event.target.matches('[role="option"]')) select(event.target);
    });
});
