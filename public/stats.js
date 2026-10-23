(function(root){
  const kinds=['movie','tv','variety','book','game','album'];
  function monthlyCounts(records,year){
    const months=Array.from({length:12},(_,i)=>({month:`${year}-${String(i+1).padStart(2,'0')}`,total:0,counts:Object.fromEntries(kinds.map(k=>[k,0]))}));
    const seen=new Set();
    for(const item of records){
      if(!kinds.includes(item.category)||!/^\d{4}-\d{2}-\d{2}$/.test(item.date||'')||Number(item.date.slice(0,4))!==Number(year))continue;
      const month=Number(item.date.slice(5,7)),day=Number(item.date.slice(8,10));
      if(month<1||month>12||day<1||day>new Date(Number(year),month,0).getDate())continue;
      if(item.id&&seen.has(item.id))continue;
      if(item.id)seen.add(item.id);
      months[month-1].total++;months[month-1].counts[item.category]++;
    }
    return months;
  }
  if(typeof module!=='undefined')module.exports={monthlyCounts};
  else root.AfterglowStats={monthlyCounts};
})(typeof window==='undefined'?globalThis:window);
