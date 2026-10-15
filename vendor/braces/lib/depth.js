'use strict';

const MAX_DEPTH = 100;

exports.MAX_DEPTH = MAX_DEPTH;
exports.checkDepth = depth => {
  if (depth > MAX_DEPTH) {
    const error = new RangeError(`Brace nesting exceeds maximum depth (${MAX_DEPTH})`);
    error.code = 'BRACES_MAX_DEPTH';
    throw error;
  }
};
