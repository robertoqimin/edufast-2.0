const {test} = require('node:test');
const assert = require('node:assert/strict');
const {configuration, SCHOOLS} = require('./demo.cjs');

test('demonstracao possui dois bancos e apps, portas loopback e nenhuma entrada publica', () => {
  const {compose, env} = configuration();
  assert.equal(compose.name, 'edufast-duas-escolas-teste');
  assert.equal(Object.keys(compose.services).length, 4);
  assert.equal(compose.services.gateway, undefined);
  for (const {id, port} of SCHOOLS) {
    const app = compose.services[`app-${id}`], db = compose.services[`db-${id}`];
    assert.deepEqual(app.ports, [`127.0.0.1:${port}:8000`]);
    assert.equal(app.environment.APP_ENV, 'development');
    assert.equal(app.environment.EDUFAST_TEST_SCHOOL, id);
    assert.equal(app.environment.DB_HOST, `db-${id}`);
    assert.equal(app.environment.DB_NAME, `edufast_${id}`);
    assert.equal(db.environment.MYSQL_DATABASE, `edufast_${id}`);
    assert.equal(db.ports, undefined);
    assert.deepEqual(db.networks, [`back-${id}`]);
    assert.equal(compose.networks[`back-${id}`].internal, true);
    assert.deepEqual(app.networks, [`local-${id}`, `back-${id}`]);
    assert.equal(compose.networks[`local-${id}`].internal, undefined);
  }
  assert.equal(env.trim().split('\n').length, 8);
});
