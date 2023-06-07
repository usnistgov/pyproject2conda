
.. automodule:: {{ fullname }}
   :autosummary:
   :autosummary-nomembers:
   :noindex:
   :no-members:
   :show-inheritance:
   :special-members: __call__, __add__, __iadd__, __sub__, __isub__, __mul__, __imul__


{% block modules %}
{% if modules %}
.. autosummary::
   :toctree:
   :template: autodocsumm/module-noindex.rst
   :recursive:
{% for item in modules %}
   {{ item }}
{%- endfor %}
{% endif %}
{% endblock %}
