

.. automodule:: {{ fullname }}
   :autosummary:
   :show-inheritance:
   :members:
   :special-members: __call__, __add__, __iadd__, __sub__, __isub__, __mul__, __imul__


{% block modules %}
{% if modules %}
.. autosummary::
   :toctree:
   :template: autodocsumm/module.rst
   :recursive:
{% for item in modules %}
   {{ item }}
{%- endfor %}
{% endif %}
{% endblock %}
