'use strict';

var pageViewModel = {
  // Page display state vars
  pageTemplate: ko.observable('index'),
  pageContext: ko.observable(),
  activePanel: ko.observable(),
  // Specific data loaded from API to build template content
  upgradeResults: ko.observable(),
  searchResults: ko.observableArray(),
  personResults: ko.observable(),
  eventResults: ko.observable(),
  yearEvents: ko.observable(),
  // Generic data loaded at all times
  upgradesRecent: ko.observableArray(),
  eventsRecent: ko.observableArray(),
  eventsYears: ko.observableArray(),
  // UI hacks
  searchSubmit: function(form){
    page('/search?' + $(form).serialize());
  },
  setActivePanel: function(tabData, element){
    var findFunc = function(){return false};
    var $root = this;
    console.log('Setting active panel for ' + $root.pageTemplate());
    switch($root.pageTemplate()) {
      case 'person':
      case 'upgrades':
        findFunc = function(){
          if (this.results.length > 0){
            $root.activePanel(this);
            return false;
          }
        }
        break;
      case 'events':
        findFunc = function(){
          if (this.events.length > 0){
            $root.activePanel(this);
            return false;
          }
        }
        break;
    }
    $.each(tabData, findFunc);
  }
};

function switchPage(context, next){
  console.log('switchPage ' + (context.prevcontext && context.prevcontext.pathname) + ' -> ' + context.pathname , arguments);
  $('.navbar-collapse').collapse('hide');
  pageViewModel.pageContext(context);
  pageViewModel.pageTemplate(context.pathname.split('/')[1] || 'index');
  scrollToHash();
};

function scrollToHash(){
  var hash = pageViewModel.pageContext() && pageViewModel.pageContext().hash
  if (hash){
    var offset = $('#' + hash).offset();
    if (offset){
      window.scrollTo(0, offset.top - 55);
      return
    }
  }
  window.scrollTo(0, 0);
}

function doUpgrades(context, next){
  if (context.state.results){
    pageViewModel.upgradeResults(context.state.results);
    next();
  } else {
    $.get('/api/v1/upgrades/', function(results){
      context.state.results = results;
      context.save();
      pageViewModel.upgradeResults(context.state.results);
    }).always(function(){
      next();
    });
  }
}

function doEvent(context, next){
  if (context.state.results){
    pageViewModel.eventResults(context.state.results);
    next();
  } else {
    $.get('/api/v1/results/event/' + context.params.id, function(results){
      context.state.results = results;
      context.save();
      pageViewModel.eventResults(context.state.results);
    }).always(function(){
      next();
    });
  }
};

function doEvents(context, next){
    page('/events/' + pageViewModel.eventsYears()[0]);
};

function doEventsYear(context, next){
  if (context.state.results){
    pageViewModel.yearEvents(context.state.results);
    next();
  } else {
    $.get('/api/v1/events/years/' + context.params.year, function(results){
      context.state.results = results;
      context.save();
      pageViewModel.yearEvents(context.state.results);
      next();
    }).fail(function(){
      page('/events');
    });
  }
};

function doPerson(context, next){
  if (context.state.results){
    pageViewModel.personResults(context.state.results);
    next();
  } else {
    $.get('/api/v1/results/person/' + context.params.id, function(results){
      context.state.results = results;
      context.save();
      pageViewModel.personResults(context.state.results);
    }).always(function(){
      next();
    });
  }
};

function doSearch(context, next){
  if (context.state.results){
    pageViewModel.searchResults(context.state.results);
    next();
  } else {
    $.get('/api/v1/people/?' + context.querystring, function(results){
      context.state.results = results;
      context.save();
      pageViewModel.searchResults(context.state.results);
    }).always(function(){
      next();
    })
  }
};

window.addEventListener('load', function() {
  $.ajaxSetup({traditional: true});

  page('/', switchPage);
  page('/search*', doSearch, switchPage);
  page('/events', doEvents, switchPage);
  page('/events/:year', doEventsYear, switchPage);
  page('/event/:id', doEvent, switchPage);
  page('/notifications', switchPage);
  page('/person/:id', doPerson, switchPage);
  page('/upgrades', doUpgrades, switchPage);

  $.get('/api/v1/upgrades/recent/', function(upgrades){
      pageViewModel.upgradesRecent(upgrades);
  });

  $.get('/api/v1/events/recent/', function(events){
      pageViewModel.eventsRecent(events);
  });

  $.get('/api/v1/events/years/', function(years){
      pageViewModel.eventsYears(years);
  });

  $.get('/html/templates.html', function(templates){
    $('body').append(templates);
    ko.options.deferUpdates = true;
    ko.applyBindings(pageViewModel);
  });

  ko.when(function(){
    return (pageViewModel.eventsRecent().length &&
            pageViewModel.eventsYears().length);
  }, function(){
    page();
  });

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/js/serviceworker.js').then(console.log);
  } 
});
