(function (global) {
  "use strict";

  function get(row) {
    if (!row?.cells?.length) {
      return {};
    }
    return row.cells[row.cells.length - 1]?.data || {};
  }

  global.GridRowMeta = global.GridRowMeta || {};
  global.GridRowMeta.get = get;
})(window);

