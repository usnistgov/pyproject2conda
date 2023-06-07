{{ fullname | escape | underline}}

.. currentmodule:: {{ module }}



.. autoclass:: {{ objname }}
   :show-inheritance:
   :inherited-members:
   :special-members: __call__, __add__, __iadd__, __sub__, __isub__, __mul__, __imul__



   {% block methods %}
   {% if methods %}


   .. rubric:: {{ _('Methods') }}
   .. autosummary::
   {% for item in methods %}
      {%- if not item.startswith('_') %}
      ~{{ name }}.{{ item }}
      {%- endif -%}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   {% block attributes %}
   {% if attributes %}


   .. rubric:: {{ _('Attributes') }}

   .. autosummary::
   {% for item in attributes %}
      ~{{ name }}.{{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}


   {% block all_methods %}
   {% if all_methods %}
   .. rubric:: {{_('Dunder Methods') }}

   .. autosummary::
   {% for item in all_methods %}
      {%- if item in [
                      '__call__',
                      '__add__',
                      '__iadd__',
                      '__sub__',
                      '__isub__',
                      '__mul__',
                      '__imul__',
                      ] %}
      ~{{ name }}.{{ item }}
      {%- endif -%}
   {%- endfor %}
   {% endif %}
   {% endblock %}
