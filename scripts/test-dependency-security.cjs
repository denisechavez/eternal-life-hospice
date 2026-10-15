'use strict';

// Run after npm ci in each sandbox and exports/outreach-tracker-src.
const assert = require('node:assert/strict');
const { test } = require('node:test');
const { readFileSync } = require('node:fs');
const { createRequire } = require('node:module');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const root = path.resolve(__dirname, '..');
const sandboxes = [
  'artifacts/review-design-sandbox',
  'artifacts/mockup-sandbox',
];
const tracker = 'exports/outreach-tracker-src';
const roots = ['.', ...sandboxes, tracker];
const requireAt = dir => createRequire(path.join(root, dir, 'package.json'));
const json = file => JSON.parse(readFileSync(file, 'utf8'));
const minimums = {
  'source-map-js': '1.2.2',
  'proxy-addr': '2.0.8',
  qs: '6.16.0',
  'postcss-selector-parser': '7.1.6',
};
const atLeast = (version, floor) => {
  const actual = version.split('.').map(Number);
  const expected = floor.split('.').map(Number);
  for (let i = 0; i < 3; i++) {
    if (actual[i] !== expected[i]) return actual[i] > expected[i];
  }
  return true;
};
const isSafeUndici = version => {
  const major = Number(version.split('.')[0]);
  const floor = { 6: '6.28.1', 7: '7.29.1', 8: '8.10.2' }[major];
  return floor && atLeast(version, floor);
};

for (const dir of roots) {
  test(`${dir}: all locked and installed copies meet security requirements`, () => {
    const lock = json(path.join(root, dir, 'package-lock.json'));
    const found = new Set();
    for (const [location, entry] of Object.entries(lock.packages)) {
      const name = location.match(/(?:^|\/)node_modules\/([^/]+)$/)?.[1];
      if (!['braces', 'undici', ...Object.keys(minimums)].includes(name)) continue;
      found.add(name);
      const installed = json(path.join(root, dir, location, 'package.json'));
      assert.equal(installed.version, entry.version, `${dir}/${location} lock/install mismatch`);
      if (name === 'braces') {
        assert.equal(entry.name, '@elh/braces-security-patch');
        assert.equal(installed.name, entry.name);
        assert.equal(entry.resolved, 'file:../../vendor/braces');
        for (const file of [
          'index.js', 'lib/depth.js', 'lib/parse.js', 'lib/compile.js',
          'lib/expand.js', 'lib/stringify.js', 'lib/utils.js',
        ]) {
          assert.equal(
            readFileSync(path.join(root, dir, location, file), 'utf8'),
            readFileSync(path.join(root, 'vendor/braces', file), 'utf8'),
            `${dir}/${location}/${file} must contain the security backport`,
          );
        }
      } else {
        assert.ok(
          name === 'undici'
            ? isSafeUndici(entry.version)
            : atLeast(entry.version, minimums[name]),
          `${dir}/${location}@${entry.version} is vulnerable`,
        );
      }
    }
    if (sandboxes.includes(dir)) {
      assert.ok(found.has('braces'));
      assert.ok(found.has('source-map-js'));
    }
    if (dir === tracker) {
      for (const name of ['undici', 'qs', 'proxy-addr', 'source-map-js']) {
        assert.ok(found.has(name), `missing tracker dependency ${name}`);
      }
    }
  });
}

for (const dir of sandboxes) {
  const localRequire = requireAt(dir);
  const braces = localRequire('braces');
  const guarded = error => error instanceof RangeError && error.code === 'BRACES_MAX_DEPTH';

  test(`${dir}: ordinary brace and glob behavior is preserved`, async () => {
    assert.deepEqual(braces.expand('src/{a,b}.{js,ts}'), [
      'src/a.js', 'src/a.ts', 'src/b.js', 'src/b.ts',
    ]);
    assert.deepEqual(braces.expand('{01..03}'), ['01', '02', '03']);
    assert.deepEqual(braces.expand('{a,{b,c}}'), ['a', 'b', 'c']);
    assert.deepEqual(braces(['a', 'a'], { expand: true, nodupes: true }), ['a']);
    assert.equal(braces.stringify(braces.parse('a/{b,c}/d')), 'a/{b,c}/d');
    assert.equal(braces.compile('a/{b,c}/d'), 'a/(b|c)/d');
    assert.throws(() => braces.expand('{1..10000}'), /range limit/);
    assert.equal(braces.compile('('.repeat(20) + 'a' + ')'.repeat(20)),
      '('.repeat(20) + 'a' + ')'.repeat(20));
    const micromatch = localRequire('micromatch');
    assert.deepEqual(micromatch(['a.js', 'b.ts', 'c.css'], '*.{js,ts}'), ['a.js', 'b.ts']);
    assert.throws(() => micromatch.braces('{'.repeat(4000) + 'a' + '}'.repeat(4000)), guarded);
    if (dir.endsWith('review-design-sandbox')) {
      const files = await localRequire('fast-glob')('src/components/mockups/**/*.tsx', {
        cwd: path.join(root, dir), ignore: ['**/_*/**', '**/_*.tsx'],
      });
      assert.ok(files.some(file => file.includes('elh-marketing-hub')));
    }
  });

  test(`${dir}: deeply nested strings fail deliberately, not by stack exhaustion`, () => {
    for (const pattern of [
      '{'.repeat(4000) + 'a,b' + '}'.repeat(4000),
      '('.repeat(4000) + 'a' + ')'.repeat(4000),
      '{('.repeat(2000) + 'a' + ')}'.repeat(2000),
      '{'.repeat(4000),
    ]) {
      for (const method of ['parse', 'compile', 'expand', 'stringify', 'create']) {
        assert.throws(() => braces[method](pattern, { maxDepth: Infinity }), guarded);
      }
      assert.throws(() => braces(pattern), guarded);
    }
  });

  test(`${dir}: direct AST callers cannot bypass walker guards`, () => {
    function deepAst() {
      const ast = { type: 'root', nodes: [] };
      let parent = ast;
      for (let i = 0; i < 4000; i++) {
        const node = { type: 'paren', parent, nodes: [] };
        parent.nodes.push(node);
        parent = node;
      }
      parent.nodes.push({ type: 'text', value: 'a' });
      return ast;
    }
    for (const method of ['compile', 'expand', 'stringify']) {
      assert.throws(() => braces[method](deepAst()), guarded);
    }
    let nested = 'a';
    for (let i = 0; i < 4000; i++) nested = [nested];
    const utils = localRequire('braces/lib/utils');
    assert.throws(() => utils.flatten(nested), guarded);
  });
}

test('proxy-addr does not trust arbitrary IPv4 clients through an IPv6 subnet', () => {
  const proxyaddr = requireAt(tracker)('proxy-addr');
  assert.equal(proxyaddr.compile('::ffff:10.0.0.0/8')('203.0.113.42'), false);
  assert.equal(proxyaddr.compile('::/1')('203.0.113.42'), false);
  const trust = proxyaddr.compile('10.0.0.0/8');
  assert.equal(trust('10.1.2.3'), true);
  assert.equal(trust('203.0.113.42'), false);
});

test('qs handles hostile constructor keys and enforces bracket/comma array limits', () => {
  const qs = requireAt(tracker)('qs');
  assert.doesNotThrow(() => qs.stringify(qs.parse(
    'x[constructor][isBuffer]=y', { plainObjects: true },
  )));
  assert.throws(() => qs.parse('a[]=1,2,3,4', {
    comma: true, arrayLimit: 3, throwOnLimitExceeded: true,
  }), RangeError);
  assert.deepEqual(qs.parse('a[]=1,2', { comma: true, arrayLimit: 3 }), { a: [['1', '2']] });
});

function childCheck(dir, source, timeout = 5000) {
  const result = spawnSync(process.execPath, ['-e', source], {
    cwd: path.join(root, dir), timeout, encoding: 'utf8',
  });
  assert.ifError(result.error);
  assert.equal(result.status, 0, result.stderr || result.stdout);
}

for (const dir of [...sandboxes, tracker]) {
  test(`${dir}: huge indexed source-map offsets do not block the event loop`, () => {
    childCheck(dir, `
      const { SourceMapConsumer, SourceNode } = require('source-map-js');
      const assert = require('node:assert/strict');
      assert.throws(() => new SourceMapConsumer({
        version: 3, sections: [{
          offset: { line: 2147483647, column: 0 },
          map: { version: 3, sources: ['a.js'], names: [], mappings: 'AAAA' }
        }]
      }), /Section offset line must not exceed/);
      const consumer = new SourceMapConsumer({
        version: 3, sources: ['a.js'], names: [], mappings: 'AAAA'
      });
      assert.equal(
        SourceNode.fromStringWithSourceMap('a', consumer).toString(), 'a'
      );
    `);
  });
}

test('selector parser handles a 400 KB flat selector without quadratic blocking', () => {
  childCheck(sandboxes[1], `
    const parser = require('postcss-selector-parser');
    const selector = '.a'.repeat(200000);
    require('node:assert/strict').equal(parser().processSync(selector), selector);
  `);
});

test('undici rejects unsolicited WebSocket subprotocols without crashing the process', () => {
  childCheck(tracker, `
    const http = require('node:http');
    const { createHash } = require('node:crypto');
    const { WebSocket } = require('undici');
    const deadline = setTimeout(() => process.exit(2), 3000);
    const server = http.createServer();
    server.on('upgrade', (request, socket) => {
      const accept = createHash('sha1').update(
        request.headers['sec-websocket-key'] + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
      ).digest('base64');
      socket.end('HTTP/1.1 101 Switching Protocols\\r\\nUpgrade: websocket\\r\\n' +
        'Connection: Upgrade\\r\\nSec-WebSocket-Accept: ' + accept +
        '\\r\\nSec-WebSocket-Protocol: unsolicited\\r\\n\\r\\n');
    });
    server.listen(0, '127.0.0.1', () => {
      const ws = new WebSocket('ws://127.0.0.1:' + server.address().port);
      ws.addEventListener('open', () => process.exit(3));
      ws.addEventListener('error', () => {
        clearTimeout(deadline);
        server.close();
      });
    });
  `);
});

test('outreach tracker Express and jsdom integrations still work', async () => {
  const localRequire = requireAt(tracker);
  const { JSDOM } = localRequire('jsdom');
  const dom = new JSDOM('<!doctype html><button id="action">Save</button>');
  let clicked = false;
  dom.window.document.querySelector('#action').addEventListener('click', () => { clicked = true; });
  dom.window.document.querySelector('#action').click();
  assert.equal(clicked, true);
  dom.window.close();

  const express = localRequire('express');
  const app = express();
  app.use(express.urlencoded({ extended: true }));
  app.post('/smoke', (req, res) => res.json(req.body));
  const server = await new Promise(resolve => {
    const listener = app.listen(0, '127.0.0.1', () => resolve(listener));
  });
  try {
    const { request } = localRequire('undici');
    const response = await request(`http://127.0.0.1:${server.address().port}/smoke`, {
      method: 'POST', headers: { 'content-type': 'application/x-www-form-urlencoded' },
      body: 'care[name]=Example',
    });
    assert.equal(response.statusCode, 200);
    assert.deepEqual(await response.body.json(), { care: { name: 'Example' } });
  } finally {
    await new Promise(resolve => server.close(resolve));
  }
});
