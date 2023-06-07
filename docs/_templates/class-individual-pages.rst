{{ fullname | escape | underline}}

.. currentmodule:: {{ module }}

.. autoclass:: {{ objname }}
   :show-inheritance:

   {% block methods %}
   ..
      .. automethod:: __init__

   {% if methods %}
   .. rubric:: {{ _('Methods') }}

   .. autosummary::
      :toctree: generated/
   {% for item in methods %}
      ~{{ name }}.{{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   {% block attributes %}
   {% if attributes %}
   .. rubric:: {{ _('Attributes') }}

   .. autosummary::
      :toctree: generated/
   {% for item in attributes %}
      ~{{ name }}.{{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   {% block all_methods %}
   {% if all_methods %}
   .. rubric:: {{_('Dunder Methods') }}

   .. autosummary::
      :toctree: generated/
   {% for item in all_methods %}
      {%- if item in ['__repr__',
                      '__len__',
                      '__call__',
                      '__next__',
                      '__iter__',
                      '__getitem__',
                      '__setitem__',
                      '__delitem__',
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
