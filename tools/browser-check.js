// Paste-run on the preview site: checks every deal picture loads and is a real image.
// Result in window.__ic: {done, total, bad:[{key,shop,title,img,why}]}
window.__ic={done:0,total:0,bad:[]};
(async()=>{
  const D=(await (await fetch('/data/deals.json',{cache:'no-store'})).json()).deals;
  window.__ic.total=D.length;let i=0;
  const one=d=>new Promise(r=>{const im=new Image();const to=setTimeout(()=>{window.__ic.bad.push({key:d.id,shop:d.shop,title:d.title,img:d.image_url||d.img,why:'timeout'});r()},20000);
    im.onload=()=>{clearTimeout(to);if(im.naturalWidth<80||im.naturalHeight<80)window.__ic.bad.push({key:d.id,shop:d.shop,title:d.title,img:im.src,why:'tiny '+im.naturalWidth});r()};
    im.onerror=()=>{clearTimeout(to);window.__ic.bad.push({key:d.id,shop:d.shop,title:d.title,img:im.src,why:'error'});r()};
    im.referrerPolicy='strict-origin-when-cross-origin';im.src=d.image_url||d.img;});
  const work=async()=>{while(i<D.length){const d=D[i++];await one(d);window.__ic.done++}};
  await Promise.all(Array.from({length:16},work));window.__ic.finished=true;
})();
'started'
