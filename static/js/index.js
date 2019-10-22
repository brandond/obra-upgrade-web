'use strict';

var pageViewModel = {
  // Page display state vars
  pageLocation: ko.observable(),
  pageTemplate: ko.observable(),
  pageContext: ko.observable(),
  activePanel: ko.observable(),
  // Specific data loaded from API to build template content
  upgradesPendingResults: ko.observable(),
  upgradesRecentResults: ko.observable(),
  searchResults: ko.observableArray(),
  personResults: ko.observable(),
  eventResults: ko.observable(),
  yearEvents: ko.observable(),
  // Generic data loaded at all times
  upgradesPending: ko.observableArray(),
  upgradesRecent: ko.observableArray(),
  eventsRecent: ko.observableArray(),
  eventsYears: ko.observableArray(),
  // UI hacks
  searchSubmit: function(form){
    page('/search?' + $(form).serialize());
  },
  changeActivePanel: function(tabData, e){
    console.log('changeActivePanel', tabData, e);
    var $root = this;
    $root.activePanel(tabData.name);
    window.location.hash = '#' + tabData.name;
  },
  setActivePanel: function(tabData, element){
    var findFunc = function(){return false};
    var $root = this;
    switch($root.pageTemplate()) {
      case 'person':
      case 'upgrades':
        findFunc = function(){
          if (window.location.hash){
            if (window.location.hash == '#' + this.name){
              $root.activePanel(this.name);
              return false;
            }
          } else if (this.results.length > 0){
            $root.activePanel(this.name);
            page.replace(window.location.pathname + '#' + this.name, undefined, false, false);
            return false;
          }
        }
        break;
      case 'events':
        findFunc = function(){
          if (window.location.hash){
            if (window.location.hash == '#' + this.name){
              $root.activePanel(this.name);
              return false;
            }
          } else if (this.events.length > 0){
            $root.activePanel(this.name);
            page.replace(window.location.pathname + '#' + this.name, undefined, false, false);
            return false;
          }
        }
        break;
    }
    $.each(tabData, findFunc);
  }
};

function switchPage(context, next){
  console.log('switchPage to ' + context.path , arguments);
  $('.navbar-collapse').collapse('hide');
  pageViewModel.pageContext(context);
  pageViewModel.pageLocation(context.pathname);
  pageViewModel.pageTemplate(context.pathname.split('/')[1] || 'index');
};

function scrollToHash(){
  console.log('scrollToHash', $(window.location.hash)[0]);
  if ($(window.location.hash).length){
    $(window.location.hash)[0].scrollIntoView({ behavior: 'smooth', block: 'start', inline: 'start'});
    return;
  }
  window.scrollTo(0, 0);
}

function doIndex(context, next){
  $.get('/api/v1/events/recent/', function(events){
    pageViewModel.eventsRecent(events);
  });
  $.get('/api/v1/upgrades/pending/top/', function(upgrades){
    pageViewModel.upgradesPending(upgrades);
  });
  $.get('/api/v1/upgrades/recent/top/', function(upgrades){
    pageViewModel.upgradesRecent(upgrades);
  });
  next();
}

function doUpgrades(context, next){
  if (context.params.type == 'pending'){
    $.get('/api/v1/upgrades/pending/', function(results){
      pageViewModel.upgradesPendingResults(results);
    });
  } else if (context.params.type == 'recent'){
    $.get('/api/v1/upgrades/recent/', function(results){
      pageViewModel.upgradesRecentResults(results);
    });
  }
  next();
}

function doEvent(context, next){
  pageViewModel.eventResults(undefined);
  $.get('/api/v1/results/event/' + context.params.id, function(results){
    pageViewModel.eventResults(results);
  }).fail(function(){
    page('/events');
  });
  next();
};

function doEvents(context, next){
  $.get('/api/v1/events/years/', function(years){
    pageViewModel.eventsYears(years);
  }).fail(function(){
    page('/');
  });

  ko.when(function(){
    return pageViewModel.eventsYears().length != 0;
  }, function(){
    page('/events/' + pageViewModel.eventsYears()[0]);
  });
};

function doEventsYear(context, next){
  pageViewModel.yearEvents(undefined);
  $.get('/api/v1/events/years/' + context.params.year + '/', function(results){
    pageViewModel.yearEvents(results);
  }).fail(function(){
    page('/events');
  });
  $.get('/api/v1/events/years/', function(years){
    pageViewModel.eventsYears(years);
  });
  next();
};

function doPerson(context, next){
  pageViewModel.personResults(undefined);
  $.get('/api/v1/results/person/' + context.params.id, function(results){
    pageViewModel.personResults(results);
  }).fail(function(){
    page('/');
  });
  next();
};

function doSearch(context, next){
  pageViewModel.searchResults([]);
  $.get('/api/v1/people/?' + context.querystring, function(results){
    pageViewModel.searchResults(results);
  })
  next();
};

window.addEventListener('load', function() {
  $.ajaxSetup({traditional: true});

  page('/', doIndex, switchPage);
  page('/search*', doSearch, switchPage);
  page('/events', doEvents, switchPage);
  page('/events/:year', doEventsYear, switchPage);
  page('/event/:id', doEvent, switchPage);
  page('/notifications', switchPage);
  page('/person/:id', doPerson, switchPage);
  page('/upgrades/:type', doUpgrades, switchPage);

  $.get('/html/templates.html', function(templates){
    $('body').append(templates);
    ko.options.deferUpdates = true;
    ko.applyBindings(pageViewModel);
  }).always(function(){
    page({'popstate': false, 'hashchange': false});
  });

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/js/serviceworker.js').then(console.log);
  }
});

window.addEventListener('popstate', (e) => {
  // The built-in popstate hook doesn't detect change and just updates all the time, including on hash changes.
  if (e.target.location.pathname == pageViewModel.pageLocation()){
    pageViewModel.activePanel(e.target.location.hash.substr(1));
  } else {
    page.replace(e.target.location.pathname, e.state);
  }
});
