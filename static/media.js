(function(){
  const fmtDate = s => {
    try{
      const d = new Date(s);
      return isNaN(d) ? s : d.toLocaleDateString('en-GB', {year:'numeric', month:'short', day:'2-digit'});
    }catch{ return s; }
  };

  const img = (path, size='w342') =>
    path ? `https://image.tmdb.org/t/p/${size}${path}` : null;

  const el = sel => document.querySelector(sel);

  function card(item, isTV){
    const poster = img(item.poster_path) || img(item.backdrop_path) || '';
    const dateLabel = isTV ? 'TV' : 'Movie';
    const dateVal   = isTV ? item.air_date : item.release_date;

    const providers = (item.providers || []).slice(0,4); // show up to 4
    const chips = providers.map(p => `
      <span class="badge">
        ${p.logo_path ? `<img src="${img(p.logo_path,'w45')}" alt="">` : ''}
        ${p.provider_name}
      </span>`).join('');

    return `
      <article class="card">
        <div class="poster" style="background-image:url('${poster||''}')"></div>
        <div class="card-body">
          <div class="title">${(item.title || item.name || 'Untitled')}</div>
          <div class="meta">
            <span>${dateLabel}</span>
            <span>•</span>
            <span>${fmtDate(dateVal)}</span>
          </div>
          <div class="overview">${item.overview || ''}</div>
          <div class="chips">${chips}</div>
        </div>
      </article>`;
  }

  async function boot(){
    // Load the prebuilt JSON (works on PI and on GitHub Pages)
    const r = await fetch('./data/media.json', {cache:'no-store'});
    const data = await r.json();

    // Movies
    const mg = el('#movies-grid'), me = el('#movies-empty');
    const tvg = el('#tv-grid'), te = el('#tv-empty');

    el('#movies-updated').textContent = data.updated ? `Updated ${data.updated}` : '';
    el('#tv-updated').textContent     = data.updated ? `Updated ${data.updated}` : '';

    if (data.movies && data.movies.length){
      mg.innerHTML = data.movies.map(m => card(m, false)).join('');
      me.classList.add('hidden');
    } else {
      mg.innerHTML = '';
      me.classList.remove('hidden');
    }

    if (data.tv && data.tv.length){
      tvg.innerHTML = data.tv.map(t => card(t, true)).join('');
      te.classList.add('hidden');
    } else {
      tvg.innerHTML = '';
      te.classList.remove('hidden');
    }
  }

  boot().catch(console.error);
})();
