const assert=require('node:assert/strict');
const {monthlyCounts}=require('../public/stats.js');
const rows=[{id:'a',category:'movie',date:'2026-01-31'},
{id:'b',category:'book',date:'2026-02-01'}, {id:'c',category:'album',date:'2026-02-28'},
{id:'d',category:'game',date:'2025-12-31'}, {id:'e',category:'tv',date:'2026-12-31'},
{id:'bad',category:'book',date:'2026-02-30'}, {id:'bad2',category:'unknown',date:'2026-02-01'}];
let months=monthlyCounts([...rows,rows[0]],2026);
assert.equal(months.length,12);assert.equal(months[0].total,1);assert.equal(months[1].total,2);
assert.equal(months[1].counts.book,1);assert.equal(months[1].counts.album,1);
assert.equal(months[2].total,0);assert.equal(months[11].total,1);
assert.equal(months.reduce((n,m)=>n+m.total,0),4);
assert.equal(monthlyCounts(rows,2025)[11].counts.game,1);
assert.equal(monthlyCounts([],2026).reduce((n,m)=>n+m.total,0),0);
assert.equal(monthlyCounts([{id:'leap',category:'book',date:'2024-02-29'}],2024)[1].total,1);
const edited=rows.map(x=>x.id==='b'?{...x,date:'2026-03-01'}:x);
assert.equal(monthlyCounts(edited,2026)[1].total,1);assert.equal(monthlyCounts(edited,2026)[2].total,1);
assert.equal(monthlyCounts(edited.filter(x=>x.id!=='c'),2026)[1].total,0);
console.log('Monthly counts: year/month boundaries, six-category counts, empty months, leap year, duplicate IDs, edits and deletes PASS');
