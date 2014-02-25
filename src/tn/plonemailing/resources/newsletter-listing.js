(function($) {
  "use strict";

  var column = {
    build: function(table, name, userSortable) {
      return clone(this, function(self) {
        self.table = table;
        self.name = name;
        self.dom = function() { return $('th.sort-on-' + name); }
        self.userSortable = userSortable;
        self.bind();
      });
    },

    sort: function() {
      var self = this;
      $.get(this.getURL(), this.getSortParams(), function(data) {
        $('#newsletterlisting-main-table').replaceWith(data);
        self.table.rebind();
      });
    },

    bind: function() {
      var self = this;

      if (this.isSortedBySelf()) {
        this.sortOrder = $('input[name="sort_order"]').val();
      } else {
        this.sortOrder = 'ascending';
      }

      if (this.userSortable) {
        this.dom().click(function() { self.sort(); });
      }
    },

    getURL: function() {
      return $('input[name="url"]').val();
    },

    getSortParams: function() {
      return {
        'sort_on': this.name,
        'sort_order': this.toggleSortOrder(),
        'pagenumber': $('input[name="pagenumber"]').val(),
        'show_all': $('input[name="show_all"]').val(),
        'nolayout': 'true'
      };
    },

    isSortedBySelf: function() {
      return $('input[name="sort_on"]').val() == this.name;
    },

    toggleSortOrder: function() {
      if (this.isSortedBySelf()) {
        if (this.sortOrder === 'ascending') {
          return this.sortOrder = 'descending';
        }
      }
      return this.sortOrder = 'ascending';
    }
  };

  var table = {
    bind: function(selector, amend) {
      return clone(this, amend);
    },

    addColumn: function(name, userSortable) {
      this._columns = this._columns || [];
      this._columns.push(column.build(this, name, userSortable));
    },

    rebind: function() {
      this._columns.forEach(function(column) { column.bind(); });
    }
  };

  $(function() {
    table.bind('#newsletterlisting-main-table', function(self) {
      self.addColumn('sortable_title', true);
      self.addColumn('sortable_last_sent', true);
    });
  });

  function clone(source, amend) {
    return (function(object) {
      amend(object);
      return object;
    })(Object.create(source))
  }
})(jQuery);
