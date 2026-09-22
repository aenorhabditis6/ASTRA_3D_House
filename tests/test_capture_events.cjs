const {test} = require('node:test');
const assert = require('node:assert/strict');
const {EventReducer, StateStore, ProgressExport} = require('../src/astra_house/assets/capture-guide.js');

const mode = {id:'m',room_id:'r',capture_id:'c',mode_plan_sha256:'a'.repeat(64),passes:[{id:'p',groups:[{id:'g',station_id:'s',shots:[{id:'one'},{id:'two'}]}]}]};
const identity = {room_id:'r',capture_id:'c',mode_id:'m',mode_plan_sha256:mode.mode_plan_sha256};
function event(seq,type,extra={}) { return {seq,t_ms:seq*1000,tz_offset_min:-420,type,...identity,...extra}; }
function shot(seq,type,id='one',extra={}) { return event(seq,type,{group_id:'g',station_id:'s',shot_ids:[id],method:'shot',...extra}); }
const start = event(1,'capture_started');

test('two undos compensate distinct actions and retain the raw audit trail', () => {
  const events=[start,shot(2,'shot_completed'),shot(3,'note_changed','one',{note:'unchanged original'}),event(4,'undo',{undoes_seq:3}),event(5,'undo',{undoes_seq:2})];
  const result=EventReducer.replay(mode,events);
  assert.equal(result.warning,null); assert.equal(result.valid_prefix_length,5);
  assert.deepEqual(result.shots.one,{status:'pending',note:''});
  assert.deepEqual(result.compensated_seqs,[3,2]); assert.equal(result.raw_events,events);
  assert.equal(EventReducer.nextUndoTarget(result.valid_events),null);
});
test('undoing a reopen restores previous completion without a station assertion', () => {
  const result=EventReducer.replay(mode,[start,shot(2,'shot_completed'),shot(3,'shot_reopened'),event(4,'undo',{undoes_seq:3})]);
  assert.equal(result.warning,null); assert.equal(result.shots.one.status,'completed');
});
test('an invalid middle reference ends replay, retains later raw events', () => {
  const events=[start,shot(2,'shot_completed'),shot(3,'shot_completed','unknown'),shot(4,'shot_completed','two')];
  const result=EventReducer.replay(mode,events);
  assert.equal(result.valid_prefix_length,2); assert.match(result.warning,/shot reference/);
  assert.equal(result.shots.two.status,'pending'); assert.equal(result.raw_events.length,4);
  const exported=ProgressExport.build({room_id:'r',capture_id:'c'},mode,result);
  assert.equal(exported.events.length,4); assert.deepEqual(exported.completed_shot_ids,['one']);
});
test('identity, order, repeated starts, no-op events and forward undos are invalid', () => {
  for (const bad of [shot(2,'shot_completed','one',{mode_id:'other'}),shot(3,'shot_completed'),event(2,'capture_started'),event(2,'undo',{undoes_seq:9}),shot(2,'shot_reopened'),shot(2,'note_changed','one',{note:''})]) {
    assert.equal(EventReducer.replay(mode,[start,bad]).valid_prefix_length,1);
  }
});
test('group completion requires all pending IDs in plan order and preserves notes', () => {
  const note=shot(2,'note_changed','one',{note:'leave original filename'});
  const group=event(3,'group_completed',{group_id:'g',station_id:'s',shot_ids:['one','two'],method:'group',within_group_order:'inferred'});
  const good=EventReducer.replay(mode,[start,note,group]);
  assert.equal(good.warning,null); assert.equal(good.shots.one.note,'leave original filename');
  assert.equal(good.shots.two.status,'completed');
  for (const ids of [['two','one'],['one'],['one','one']]) assert.equal(EventReducer.replay(mode,[start,note,{...group,shot_ids:ids}]).valid_prefix_length,2);
});
function memoryStorage() {
  const values = new Map();
  return {get length(){return values.size;}, key:i=>[...values.keys()][i],getItem:k=>values.has(k)?values.get(k):null,setItem:(k,v)=>values.set(k,v),removeItem:k=>values.delete(k)};
}
test('corrupt bytes quarantine before replacement and stale hashes stay discoverable', () => {
  const storage=memoryStorage(), store=new StateStore({room_id:'r',capture_id:'c'},storage);
  storage.setItem(store.key(mode),'{bad'); storage.setItem(store.prefix(mode)+'old',JSON.stringify({events:[start]}));
  assert.deepEqual(store.load(mode).events,[]);
  const stale=store.findStale(mode);
  assert.equal(stale.length,2); assert.ok(stale.some(s=>s.raw==='{bad'));
  store.save(mode,[start],'g'); assert.equal(store.findStale(mode).length,2);
});
test('failed quarantine preserves unreadable data and writes continue only in memory', () => {
  const storage=memoryStorage(), store=new StateStore({room_id:'r',capture_id:'c'},storage), key=store.key(mode);
  storage.setItem(key,'{bad'); storage.setItem=()=>{throw new Error('full');};
  store.load(mode); store.save(mode,[start],'g');
  assert.equal(storage.getItem(key),'{bad'); assert.equal(store.load(mode).events.length,1);
  assert.match(store.persistenceWarning,/lose progress/);
});
test('invalid cursor does not erase valid events and modes remain separate', () => {
  const store=new StateStore({room_id:'r',capture_id:'c'},memoryStorage());
  store.save(mode,[start],'unknown');
  const other={...mode,id:'second'}; store.save(other,[],'g'); store.reset(other);
  assert.equal(store.load(mode).events.length,1); assert.equal(store.load(mode).last_group_id,'unknown');
});
