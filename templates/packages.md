{% for pkg in packages %}
# {{ pkg['name'] }} ({{ pkg['stars']|default(0, true) }} stars)

> {{ pkg['path'] }}

{{ pkg['synopsis']|default('No synopsis provided.', true) }} [Read more on GoDoc](https://godoc.org/{{ pkg['path'] }}).

{% if not loop.last %}
---
{% endif %}

{% endfor %}
