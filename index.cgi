#!/usr/bin/env perl

# HOW TO USE:
# create a file in the same path as this script called 'my_token' with your api token
# create a file in the same path as this script called 'usernames' with the list of github usernames to search for

use Mojolicious::Lite;
use Mojolicious::Plugin::TtRenderer;
plugin 'tt_renderer';

use FindBin qw($Bin);
use JSON;
use Net::GitHub;

get '/' => sub {
    my $c = shift;

    my $e = $c->github->event;


    # looks up recent activity for the given list of usernames
    # and finds both pull requests and push events
    # and gets a count of pushes, opened prs, closed prs (and if they were merged)
    # and counts the number of lines affected (adding additions and deletions)
    my $counts = {};
    my $keep = [];
    foreach my $username (@{ $c->usernames }) {
        my $events = $e->user_public_events($username);
        $c->app->log->debug("$username => " . scalar(@$events));
        # FIXME: doesn't handle paging
        foreach my $event (@$events) {
            my $type = $event->{'type'};
            next if $type !~ /^(Push|PullRequest)Event$/;
            next if $event->{'created_at'} lt '2015-12-17';
            push @$keep, $event;
	    my $submitter = $event->{'payload'}->{'pull_request'}->{'user'}->{'login'} || $username;
            $counts->{$submitter}->{'username'} ||= $submitter;
            my $action = $event->{'payload'}->{'action'} || $type;
            $counts->{$submitter}->{'merged'}++ if $event->{'payload'}->{'pull_request'}->{'merged'};
            $counts->{$submitter}->{$action}++;
            $counts->{$submitter}->{'lines'} += $event->{'payload'}->{'pull_request'}->{'additions'} || 0;
            $counts->{$submitter}->{'lines'} += $event->{'payload'}->{'pull_request'}->{'deletions'} || 0;
        }
    }

    # list of recent events
    $c->stash(keep => $keep);

    # usernames sorted by most pull requests, followed by merged pull requests, followed by lines modified, followed by number of pushes
    my $sorted = [
        sort {
            ($b->{'opened'} || 0)       <=> ($a->{'opened'} || 0)
            || ($b->{'merged'} || 0)    <=> ($a->{'merged'} || 0)
            || ($b->{'lines'} || 0)     <=> ($b->{'lines'} || 0)
            || ($b->{'PushEvent'} || 0) <=> ($a->{'PushEvent'} || 0)
        } values %$counts
    ];
    $c->stash(counts => $sorted);

    $c->render(template => 'index');
};

helper github => sub { my $c = shift; $c->{'github'} ||= Net::GitHub->new(access_token => $c->token) };

# parse personal token from 'my_token' file
# TODO: read username/password and use oauth as fallback
helper token => sub {
    my $c = shift;

    return $c->{'token'} ||= do {
        my $err = "Unable to find your token on first line of 'my_token' file (perhaps you didn't create it yet?)\n";
        open my $token_fh, '<', $Bin . '/my_token' or die $err; # conveniently .gitignored (for security!)
        my $token = <$token_fh> // die $err;
        close $token_fh;

        $token;
    }
};

helper usernames => sub {
    my $c = shift;

    return $c->{'usernames'} ||= do {
       my $err = "Unable to find list of github usernames from 'usernames' files (perhaps you didn't create it yet?)\n";
       open my $username_fh, '<', $Bin . '/usernames' or die $err;
       my @usernames = <$username_fh>;
       chomp @usernames;

       \@usernames;
    };
};

app->secrets(['Bluehost Christmas Hackathon']);
app->renderer->default_handler( 'tt' );
app->start;
__DATA__

@@ index.html.tt
[% WRAPPER 'layouts/default.html.tt', title => 'Welcome to the Bluehost Christmas Hackathon' %]
        <nav class="navbar navbar-default">
          <div class="container">
            <div class="navbar-header">
              <button type="button" class="navbar-toggle collapsed" data-toggle="collapse" data-target="#navbar" aria-expanded="false" aria-controls="navbar">
                <span class="sr-only">Toggle navigation</span>
                <span class="icon-bar"></span>
                <span class="icon-bar"></span>
                <span class="icon-bar"></span>
              </button>
            </div>
	    <h1>Bluehost Christmas Hackathon Leaderboard</h1>
            <div id="navbar" class="collapse navbar-collapse">
            </div><!--/.nav-collapse -->
          </div>
        </nav>

        <div class="container-fluid">
        <div class="row">
            <div class="col-md-6">
            <div>
                <div class="panel panel-default panel-primary">
                    <div class="panel-heading">Leaders</div>
                    <div class="panel-body">
<!--pre> [%# h.dumper(counts) %] </pre-->
                        <table class="table table-striped table-bordered">
                        <tr><th>Username</th><th>Pull Requests Opened</th><th>Pull Requests Merged</th><th>Pushes</th><th>Lines</th></tr>
                        [% FOREACH count IN counts %]
                        <tr><td>[% count.username %]</td><td>[% count.opened %]</td><td>[% count.merged %]</td><td>[% count.PushEvent %]</td><td>[% count.lines %]</td></tr>
                        [% END %]
                        </table>
                    </div>
                </div>
            </div>
            </div>
            <div class="col-md-6">
                <div class="panel panel-default panel-primary">
                    <div class="panel-heading">Events</div>
                    <div class="panel-body">
[% keep.size %]
<ul class="list-group">
[% FOREACH event IN keep.sort('created_at').reverse %]
<li class="list-group-item clearfix">
  <div class="requestor left">
    <div><img alt="$requestor_name" class="gravatar" height="45" width="45" src="[% event.actor.avatar_url %]v=3&s=60"></div>
    <div>[% event.actor.login %]</div>
  </div>
  <div class="status right"><a type="a" class="btn btn-info">[% event.payload.action || event.type %]</a></div>
  <div class="summary left">
      <div>
          <a class="issue-title-link issue-nwo-link" href="https://github.com/[% event.repo.name %]">[% event.repo.name %]</a>
          <a class="issue-title-link" href="[% event.payload.pull_request._links.html %]">[% event.payload.title || event.payload.head %]</a>
	  <div>Created at [% event.created_at %]</div>
      </div>
      <!--pre>[%# h.dumper(event) %]</pre-->
  </div>
</li>
[% END %]
</ul>
</div>
</div>
</div>
</div>
</div>
<pre>[%# h.dumper(ua) %]</pre>
<pre>
[%# h.dumper(keep) %]
</pre>
[% END %]

@@ layouts/default.html.tt
<!DOCTYPE html>
<html>
  <head>
    <title>[% title %]</title>
        <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.4/css/bootstrap.min.css">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta http-equiv="refresh" content="60">
        <style>
            /* from github.com */
            a { text-decoration: none }
            a:active, a:hover { outline: 0px none; text-decoration: none; }

            .issue-title-link { padding-right: 3px; margin-bottom: 2px; font-size: 15px; font-weight: bold; line-height: 1.2; color: #333 }
            .issue-title-link:hover { color: #4078C0; }
            .issue-nwo-link { color: #767676; }

            /* new stuff */
            .left  { float: left; }
            .right { float: right; }
            .cr    { clear: right; }

            .requestor { min-width: 10em; text-align: center; }
            .status .btn { min-width: 6em; font-weight: bold; }
            .summary { margin-left: 2em; max-width: 60%; overflow: ellipsis; }
            .special { background-color: yellow; }
            .glyphicon { top: 3px; }

            /* old stuff */
            /*  
            .time { color: #bbb; font-size: 75%; }
            .pull_request { border-top: 1px solid #dfdfdf; padding: 15px; }
            .summary { font-weight: bold }
            .title { color: #666; font-size: 85% }
            .merged { color: red; font-size: 40px; }
            */
        </style>
  </head>
  <body>[% content %]</body>
</html>
