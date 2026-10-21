// Small progressive enhancement: submit the search form on Enter and focus the query when requested.
document.addEventListener('DOMContentLoaded', () => {
  const search = document.querySelector('#medicine-search');
  if (search && new URLSearchParams(window.location.search).has('q')) {
    search.setAttribute('aria-label', 'Search medicine; current results are filtered by this query');
  }
});
