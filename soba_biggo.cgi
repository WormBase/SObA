#!/usr/bin/perl 

# partially cleaned up amigo.cgi from 12.204 to only produce SObA  2016 12 14


use CGI;
use strict;
use LWP::Simple;
use LWP::UserAgent;
use JSON;
use Tie::IxHash;                                # allow hashes ordered by item added


use Storable qw(dclone);			# copy hash of hashes

use Time::HiRes qw( time );
my $startTime = time; my $prevTime = time;
$startTime =~ s/(\....).*$/$1/;
$prevTime  =~ s/(\....).*$/$1/;

# use DBI;
# my $dbh = DBI->connect ( "dbi:Pg:dbname=testdb;host=", "postgres", "") or die "Cannot connect to database!\n";     # for remote access
# my $result;

my $json = JSON->new->allow_nonref;
my $query = new CGI;
# my $base_solr_url = 'http://golr.berkeleybop.org/';		# GO golr server
my $base_solr_url = 'http://wobr2.caltech.edu:8080/solr/biggo/';		# big geneontology golr server


my %paths;	# finalpath => array of all (array of nodes of paths that end)
		# childToParent -> child node -> parent node => relationship
		# # parentToChild -> parent node -> child node => relationship

  my %nodesAll;								# for an annotated phenotype ID, all nodes in its topological map that have transitivity
  my %edgesAll;								# for an annotated phenotype ID, all edges in its topological map that have transitivity
  my %ancestorNodes;

&process();

sub process {
  my $action;                   # what user clicked
  unless ($action = $query->param('action')) { $action = 'none'; }

#   &printHtmlHeader(); 
#   print "If you're using this, talk to Juancarlos<br/>";
  if ($action eq 'annotSummaryCytoscape')      { &annotSummaryCytoscape('all_roots'); }
    elsif ($action eq 'annotSummaryGraph')          { &annotSummaryGraph();     }
#     elsif ($action eq 'update graph')               { &annotSummaryCytoscape(); }
    elsif ($action eq 'annotSummaryJson')           { &annotSummaryJson();      }	# temporarily keep this for the live www.wormbase going through the fake phenotype_graph_json widget
    elsif ($action eq 'annotSummaryJsonp')          { &annotSummaryJsonp();     }	# new jsonp widget to get directly from .wormbase without fake widget
    elsif ($action eq 'frontPage')          { &frontPage();     }	# autocomplete on gene names
    elsif ($action eq 'autocompleteXHR') {            &autocompleteXHR(); }

    else { &frontPage(); }				# no action, show dag by default
} # sub process

sub autocompleteXHR {
  print "Content-type: text/html\n\n";
  my ($var, $words) = &getHtmlVar($query, 'query');
  unless ($words) { ($var, $words) = &getHtmlVar($query, 'query'); }
  ($var, my $field) = &getHtmlVar($query, 'field');
  if ($field eq 'Gene') { &autocompleteGene($words); }
} # sub autocompleteXHR

sub autocompleteGene {
  my ($words) = @_;
  my ($var, $taxonFq) = &getHtmlVar($query, 'taxonFq');
  my $max_results = 20; 
#   if ($words =~ m/^.{5,}/) { $max_results = 500; }	# always only have 20 results
  my $escapedWords = $words;
  my $lcwords = lc($escapedWords);
  my $ucwords = uc($escapedWords);
#   $escapedWords =~ s/ /\\ /g;
  $escapedWords =~ s/ /%5C%20/g;
  $escapedWords =~ s/:/\\:/g;
  my %matches; my $t = tie %matches, "Tie::IxHash";     # sorted hash to filter results

#   my $solr_taxon_url = 'http://wobr2.caltech.edu:8080/solr/biggo/select?qt=standard&fl=id,taxon,taxon_label&version=2.2&wt=json&rows=0&indent=on&q=*:*&facet=true&facet.field=taxon_label&facet.mincount=1&fq=document_category:%22bioentity%22';

#   my $solr_gene_url = 'http://wobr2.caltech.edu:8080/solr/biggo/select?qt=standard&fl=score,id,bioentity_label,bioentity_internal_id,bioentity_name,taxon,taxon_label&version=2.2&wt=json&rows=' . $max_results . '&indent=on&q=*:*&fq=document_category:%22bioentity%22&fq=(bioentity_internal_id:*' . $lcwords . '*+OR+bioentity_internal_id:*' . $ucwords . '*+OR+bioentity_label:*' . $lcwords . '*+OR+bioentity_label:*' . $ucwords . '*+OR+bioentity_name:*' . $lcwords . '*+OR+bioentity_name:*' . $ucwords . '*)';
#   my $solr_gene_url = 'http://wobr2.caltech.edu:8080/solr/biggo/select?qt=standard&fl=score,id,bioentity_label,bioentity_name,taxon,taxon_label&version=2.2&wt=json&rows=' . $max_results . '&indent=on&q=*:*&fq=document_category:%22bioentity%22&fq=(bioentity_label:*' . $lcwords . '*+OR+bioentity_label:*' . $ucwords . '*+OR+bioentity_name:*' . $lcwords . '*+OR+bioentity_name:*' . $ucwords . '*)';

#  try to also query for id, doesn't work.
#   my $solr_gene_url = 'http://wobr2.caltech.edu:8080/solr/biggo/select?qt=standard&fl=score,id,bioentity_label,bioentity_name,taxon,taxon_label&version=2.2&wt=json&rows=' . $max_results . '&indent=on&q=*:*&fq=document_category:%22bioentity%22&fq=(id:' . $lcwords . '*+OR+id:' . $ucwords . '*+OR+bioentity_label:' . $lcwords . '*+OR+bioentity_label:' . $ucwords . '*+OR+bioentity_name:' . $lcwords . '*+OR+bioentity_name:' . $ucwords . '*)';

# old way
#   my $solr_gene_url = 'http://wobr2.caltech.edu:8080/solr/biggo/select?qt=standard&fl=score,id,bioentity_label,bioentity_name,taxon,taxon_label&version=2.2&wt=json&rows=' . $max_results . '&indent=on&q=*:*&fq=document_category:%22bioentity%22&fq=(bioentity_label:' . $lcwords . '*+OR+bioentity_label:' . $ucwords . '*+OR+bioentity_name:' . $lcwords . '*+OR+bioentity_name:' . $ucwords . '*)';

# _searchable way
#   my $solr_gene_url = 'http://wobr2.caltech.edu:8080/solr/biggo/select?qt=standard&fl=score,id,bioentity_label,bioentity_name,taxon,taxon_label&version=2.2&wt=json&rows=500&indent=on&q=*:*&fq=document_category:%22bioentity%22&fq=(id:"' . $escapedWords . '"*+OR+bioentity_label_searchable:"' . $escapedWords . '"*+OR+bioentity_name_searchable:"' . $escapedWords . '"*)';
#   my $solr_gene_url = 'http://wobr2.caltech.edu:8080/solr/biggo/select?qt=standard&fl=score,id,bioentity_label,bioentity_name,taxon,taxon_label&version=2.2&wt=json&rows=500&indent=on&q=*:*&fq=document_category:%22bioentity%22&fq=(id:' . $escapedWords . '+OR+bioentity_label_searchable:' . $escapedWords . '+OR+bioentity_name_searchable:' . $escapedWords . ')';

#   my $solr_gene_url = 'http://wobr2.caltech.edu:8080/solr/biggo/select?qt=standard&fl=score,id,bioentity_label,bioentity_name,taxon,taxon_label&version=2.2&wt=json&rows=500&indent=on&q=*:*&fq=document_category:%22bioentity%22&fq=(id:' . $escapedWords . '+OR+bioentity_label_searchable:' . $escapedWords . '+OR+bioentity_name_searchable:' . $escapedWords . ')';

  
#   my $page_data = get $solr_gene_url;
# 
# # print qq(PD $page_data PD);
#   
#   my $perl_scalar = $json->decode( $page_data );
#   my %jsonHash = %$perl_scalar;
# 
# # print "YES";
# #   my $topoHashref = $json->decode( $jsonHash{"response"}{"docs"}[0] );
# #   my $topoHashref = $json->decode( $jsonHash{"responseHeader"} );
# # print "NO";
# 
# #   my $topoHashref = $jsonHash{"response"}{"docs"}[0];
# #   my %topoHash = %$topoHashref;
# #   $matches{$topoHash{id}}++;
#   foreach my $geneHash (@{ $jsonHash{"response"}{"docs"} }) {
#     my %geneHash = %$geneHash;
#     my $id = $geneHash{id} || '-';
#     my $taxon_label = $geneHash{taxon_label} || '-';
#     my $bioentity_label = $geneHash{bioentity_label} || '-';
#     my $bioentity_name = $geneHash{bioentity_name} || '-';
# #     my $bioentity_internal_id = $geneHash{bioentity_internal_id} || '-';
# #     my $entry = qq($id - $taxon_label - $bioentity_name - $bioentity_label - $bioentity_internal_id);
# #     my $entry = qq($bioentity_name ($taxon_label, $id, $bioentity_label, $bioentity_internal_id));
#     my $entry = qq($bioentity_label ($taxon_label, $id, $bioentity_name));
#     $matches{$entry}++; 
#   }
#   if (scalar (@{ $jsonHash{"response"}{"docs"} }) >= $max_results) { $matches{"more results, type more to narrow your search"}++; }


# print qq(WORDS $words ESCAPED $escapedWords END<br/>\n);

# Exact match (case sensitive)
  my $solr_gene_url = 'http://wobr2.caltech.edu:8080/solr/biggo/select?qt=standard&fl=score,id,bioentity_internal_id,synonym,bioentity_label,bioentity_name,taxon,taxon_label&version=2.2&wt=json&rows=' . $max_results . '&indent=on&q=*:*&fq=document_category:%22bioentity%22&fq=(bioentity_internal_id:' . $escapedWords . '+OR+bioentity_label:' . $escapedWords . '+OR+bioentity_name:' . $escapedWords . '+OR+synonym:' . $escapedWords . ')';
#   my $solr_gene_url = 'http://wobr2.caltech.edu:8080/solr/biggo/select?qt=standard&fl=score,id,bioentity_internal_id,synonym,bioentity_label,bioentity_name,taxon,taxon_label&version=2.2&wt=json&rows=' . $max_results . '&indent=on&q=*:*&fq=document_category:%22bioentity%22&fq=(bioentity_internal_id:' . $words . '+OR+bioentity_label:' . $words . '+OR+bioentity_name:' . $words . '+OR+synonym:' . $words . ')';
  if ($taxonFq) { $solr_gene_url .= "&fq=($taxonFq)"; }
  my ($matchesHashref) = &solrSearch( $solr_gene_url, \%matches, $max_results);
  %matches = %$matchesHashref;

# String wildcard match (case sensitive)
  my $matchesCount = scalar keys %matches;
  if ($matchesCount < $max_results) {
    my $extraMatchesCount = $max_results - $matchesCount;
   $solr_gene_url = 'http://wobr2.caltech.edu:8080/solr/biggo/select?qt=standard&fl=score,id,bioentity_internal_id,synonym,bioentity_label,bioentity_name,taxon,taxon_label&version=2.2&wt=json&rows=' . $max_results . '&indent=on&q=*:*&fq=document_category:%22bioentity%22&fq=(bioentity_internal_id:' . $escapedWords . '*+OR+bioentity_label:' . $escapedWords . '*+OR+bioentity_name:' . $escapedWords . '*+OR+synonym:' . $escapedWords . '*)';
#    $solr_gene_url = 'http://wobr2.caltech.edu:8080/solr/biggo/select?qt=standard&fl=score,id,bioentity_internal_id,synonym,bioentity_label,bioentity_name,taxon,taxon_label&version=2.2&wt=json&rows=' . $max_results . '&indent=on&q=*:*&fq=document_category:%22bioentity%22&fq=(bioentity_internal_id:' . $words . '*+OR+bioentity_label:' . $words . '*+OR+bioentity_name:' . $words . '*+OR+synonym:' . $words . '*)';
    if ($taxonFq) { $solr_gene_url .= "&fq=($taxonFq)"; }
    my ($matchesHashref) = &solrSearch( $solr_gene_url, \%matches, $max_results);
    %matches = %$matchesHashref;
  }

  my @words; my $isPhrase = 0;
  if ($words =~ m/[\s\-]/) { 
    $isPhrase++;
    (@words) = split/[\s\-]/, $words; }

  if ($isPhrase) {
      my $lastWord = pop @words;
      my $firstWord = join" ", @words;
      my $extraMatchesCount = $max_results - $matchesCount;
      $solr_gene_url = 'http://wobr2.caltech.edu:8080/solr/biggo/select?qt=standard&fl=score,id,bioentity_internal_id,synonym,bioentity_label,bioentity_name,taxon,taxon_label&version=2.2&wt=json&rows=' . $max_results . '&indent=on&q=*:*&fq=document_category:%22bioentity%22&fq=((bioentity_internal_id_searchable:"' . $firstWord . '"+AND+bioentity_internal_id_searchable:' . $lastWord . '*)+OR+(bioentity_name_searchable:"' . $firstWord . '"+AND+bioentity_name_searchable:' . $lastWord . '*)+OR+(bioentity_label_searchable:"' . $firstWord . '"+AND+bioentity_label_searchable:' . $lastWord . '*)+OR+(synonym_searchable:"' . $firstWord . '"+AND+synonym_searchable:' . $lastWord . '*))';

# http://wobr2.caltech.edu:8080/solr/biggo/select?qt=standard&fl=score,id,bioentity_internal_id,bioentity_label,bioentity_name,synonym,taxon,taxon_label&version=2.2&wt=json&rows=500&indent=on&q=*:*&fq=document_category:%22bioentity%22&fq=


      if ($taxonFq) { $solr_gene_url .= "&fq=($taxonFq)"; }
      my ($matchesHashref) = &solrSearch( $solr_gene_url, \%matches, $max_results);
      %matches = %$matchesHashref;
    } else {		# not a phrase

    # Exact match (case insensitive _searchable)
      $matchesCount = scalar keys %matches;
      if ($matchesCount < $max_results) {
        my $extraMatchesCount = $max_results - $matchesCount;
        $solr_gene_url = 'http://wobr2.caltech.edu:8080/solr/biggo/select?qt=standard&fl=score,id,bioentity_internal_id,synonym,bioentity_label,bioentity_name,taxon,taxon_label&version=2.2&wt=json&rows=' . $max_results . '&indent=on&q=*:*&fq=document_category:%22bioentity%22&fq=(bioentity_internal_id_searchable:' . $escapedWords . '+OR+bioentity_label_searchable:' . $escapedWords . '+OR+bioentity_name_searchable:' . $escapedWords . '+OR+synonym_searchable:' . $escapedWords . ')';
        if ($taxonFq) { $solr_gene_url .= "&fq=($taxonFq)"; }
        my ($matchesHashref) = &solrSearch( $solr_gene_url, \%matches, $max_results);
        %matches = %$matchesHashref;
      }

    # Starting with word Wildcard match (case insensitive _searchable)
      $matchesCount = scalar keys %matches;
      if ($matchesCount < $max_results) {
        my $extraMatchesCount = $max_results - $matchesCount;
        $solr_gene_url = 'http://wobr2.caltech.edu:8080/solr/biggo/select?qt=standard&fl=score,id,bioentity_internal_id,synonym,bioentity_label,bioentity_name,taxon,taxon_label&version=2.2&wt=json&rows=' . $max_results . '&indent=on&q=*:*&fq=document_category:%22bioentity%22&fq=(bioentity_internal_id_searchable:' . $escapedWords . '*+OR+bioentity_label_searchable:' . $escapedWords . '*+OR+bioentity_name_searchable:' . $escapedWords . '*+OR+synonym_searchable:' . $escapedWords . '*)';
        if ($taxonFq) { $solr_gene_url .= "&fq=($taxonFq)"; }
        my ($matchesHashref) = &solrSearch( $solr_gene_url, \%matches, $max_results);
        %matches = %$matchesHashref;
      }

    # Wildcard anywhere match (case insensitive _searchable)	# Raymond doesn't want that
#       $matchesCount = scalar keys %matches;
#       if ($matchesCount < $max_results) {
#         my $extraMatchesCount = $max_results - $matchesCount;
#         $solr_gene_url = 'http://wobr2.caltech.edu:8080/solr/biggo/select?qt=standard&fl=score,id,bioentity_internal_id,synonym,bioentity_label,bioentity_name,taxon,taxon_label&version=2.2&wt=json&rows=' . $max_results . '&indent=on&q=*:*&fq=document_category:%22bioentity%22&fq=(bioentity_internal_id_searchable:*' . $escapedWords . '*+OR+bioentity_label_searchable:*' . $escapedWords . '*+OR+bioentity_name_searchable:*' . $escapedWords . '*+OR+synonym_searchable:*' . $escapedWords . '*)';
#         if ($taxonFq) { $solr_gene_url .= "&fq=($taxonFq)"; }
#         my ($matchesHashref) = &solrSearch( $solr_gene_url, \%matches, $max_results);
#         %matches = %$matchesHashref;
#       }
  }




# id:word*
#   my $solr_gene_url = 'http://wobr2.caltech.edu:8080/solr/biggo/select?qt=standard&fl=score,id,synonym,bioentity_label,bioentity_name,taxon,taxon_label&version=2.2&wt=json&rows=500&indent=on&q=*:*&fq=document_category:%22bioentity%22&fq=(id:' . $escapedWords . '*)';


#   my $matches = join"<br/>\n", keys %matches;
#   print qq(<br>Q1 MATCHES $matches<br>END Q1<br><br>);

# id:*word* -id:word*
#     $solr_gene_url = 'http://wobr2.caltech.edu:8080/solr/biggo/select?qt=standard&fl=score,id,bioentity_label,bioentity_name,taxon,taxon_label&version=2.2&wt=json&rows=500&indent=on&q=*:*&fq=document_category:%22bioentity%22&fq=(-id:' . $escapedWords . '*)&fq=(id:*' . $escapedWords . '*)';

#   my $matchesCount = scalar keys %matches;
#   if ($matchesCount < $max_results) {
#     my $extraMatchesCount = $max_results - $matchesCount;
#     $solr_gene_url = 'http://wobr2.caltech.edu:8080/solr/biggo/select?qt=standard&fl=score,id,bioentity_label,bioentity_name,taxon,taxon_label&version=2.2&wt=json&rows=500&indent=on&q=*:*&fq=document_category:%22bioentity%22&fq=(-id:' . $escapedWords . '*)&fq=(id:*' . $escapedWords . '*)';
#     if ($taxonFq) { $solr_gene_url .= "&fq=($taxonFq)"; }
#     my ($matchesHashref) = &solrSearch( $solr_gene_url, \%matches, $max_results);
#     %matches = %$matchesHashref;
#   }

# _searchable:"word"
#     $solr_gene_url = 'http://wobr2.caltech.edu:8080/solr/biggo/select?qt=standard&fl=score,id,bioentity_label,bioentity_name,taxon,taxon_label&version=2.2&wt=json&rows=500&indent=on&q=*:*&fq=document_category:%22bioentity%22&fq=(bioentity_label_searchable:"' . $words . '"+OR+bioentity_name_searchable:"' . $words . '")';
#   $matchesCount = scalar keys %matches;
#   if ($matchesCount < $max_results) {
#     my $extraMatchesCount = $max_results - $matchesCount;
#     $solr_gene_url = 'http://wobr2.caltech.edu:8080/solr/biggo/select?qt=standard&fl=score,id,bioentity_label,bioentity_name,taxon,taxon_label&version=2.2&wt=json&rows=500&indent=on&q=*:*&fq=document_category:%22bioentity%22&fq=(bioentity_label_searchable:"' . $words . '"+OR+bioentity_name_searchable:"' . $words . '")';
#     if ($taxonFq) { $solr_gene_url .= "&fq=($taxonFq)"; }
#     my ($matchesHashref) = &solrSearch( $solr_gene_url, \%matches, $max_results);
#     %matches = %$matchesHashref;
#   }

# fields:word*
#     $solr_gene_url = 'http://wobr2.caltech.edu:8080/solr/biggo/select?qt=standard&fl=score,id,bioentity_label,bioentity_name,taxon,taxon_label&version=2.2&wt=json&rows=' . $max_results . '&indent=on&q=*:*&fq=document_category:%22bioentity%22&fq=(bioentity_label:' . $lcwords . '*+OR+bioentity_label:' . $ucwords . '*+OR+bioentity_name:' . $lcwords . '*+OR+bioentity_name:' . $ucwords . '*)';
#   $matchesCount = scalar keys %matches;
#   if ($matchesCount < $max_results) {
#     my $extraMatchesCount = $max_results - $matchesCount;
#     $solr_gene_url = 'http://wobr2.caltech.edu:8080/solr/biggo/select?qt=standard&fl=score,id,bioentity_label,bioentity_name,taxon,taxon_label&version=2.2&wt=json&rows=' . $max_results . '&indent=on&q=*:*&fq=document_category:%22bioentity%22&fq=(bioentity_label:' . $lcwords . '*+OR+bioentity_label:' . $ucwords . '*+OR+bioentity_name:' . $lcwords . '*+OR+bioentity_name:' . $ucwords . '*)';
#     if ($taxonFq) { $solr_gene_url .= "&fq=($taxonFq)"; }
#     my ($matchesHashref) = &solrSearch( $solr_gene_url, \%matches, $max_results);
#     %matches = %$matchesHashref;
#   }

# fields:*word* -fields:word*
#     $solr_gene_url = 'http://wobr2.caltech.edu:8080/solr/biggo/select?qt=standard&fl=score,id,bioentity_label,bioentity_name,taxon,taxon_label&version=2.2&wt=json&rows=' . $extraMatchesCount . '&indent=on&q=*:*&fq=document_category:%22bioentity%22&fq=(-bioentity_label:' . $lcwords . '*+AND+-bioentity_label:' . $ucwords . '*+AND+-bioentity_name:' . $lcwords . '*+AND+-bioentity_name:' . $ucwords . '*)&fq=(bioentity_label:*' . $lcwords . '*+OR+bioentity_label:*' . $ucwords . '*+OR+bioentity_name:*' . $lcwords . '*+OR+bioentity_name:*' . $ucwords . '*)';
#   $matchesCount = scalar keys %matches;
#   if ($matchesCount < $max_results) {
#     my $extraMatchesCount = $max_results - $matchesCount;
#     $solr_gene_url = 'http://wobr2.caltech.edu:8080/solr/biggo/select?qt=standard&fl=score,id,bioentity_label,bioentity_name,taxon,taxon_label&version=2.2&wt=json&rows=' . $extraMatchesCount . '&indent=on&q=*:*&fq=document_category:%22bioentity%22&fq=(-bioentity_label:' . $lcwords . '*+AND+-bioentity_label:' . $ucwords . '*+AND+-bioentity_name:' . $lcwords . '*+AND+-bioentity_name:' . $ucwords . '*)&fq=(bioentity_label:*' . $lcwords . '*+OR+bioentity_label:*' . $ucwords . '*+OR+bioentity_name:*' . $lcwords . '*+OR+bioentity_name:*' . $ucwords . '*)';
#     if ($taxonFq) { $solr_gene_url .= "&fq=($taxonFq)"; }
#     my ($matchesHashref) = &solrSearch( $solr_gene_url, \%matches, $max_results);
#     %matches = %$matchesHashref;
#   }

#   my $matchesCount = scalar keys %matches;
#   if ($matchesCount < $max_results) {
#     my $extraMatchesCount = $max_results - $matchesCount;
#     
# #     my $solr_gene_url = 'http://wobr2.caltech.edu:8080/solr/biggo/select?qt=standard&fl=score,id,bioentity_label,bioentity_name,taxon,taxon_label&version=2.2&wt=json&rows=' . $extraMatchesCount . '&indent=on&q=*:*&fq=document_category:%22bioentity%22&fq=(-bioentity_label:' . $lcwords . '*+AND+-bioentity_label:' . $ucwords . '*+AND+-bioentity_name:' . $lcwords . '*+AND+-bioentity_name:' . $ucwords . '*)&fq=(bioentity_label:*' . $lcwords . '*+OR+bioentity_label:*' . $ucwords . '*+OR+bioentity_name:*' . $lcwords . '*+OR+bioentity_name:*' . $ucwords . '*)';
#     if ($taxonFq) { $solr_gene_url .= "&fq=($taxonFq)"; }
#     my $page_data = get $solr_gene_url;
#     my $perl_scalar = $json->decode( $page_data );
#     my %jsonHash = %$perl_scalar;
# 
#     foreach my $geneHash (@{ $jsonHash{"response"}{"docs"} }) {
#       my %geneHash = %$geneHash;
#       my $id = $geneHash{id} || '-';
#       my $taxon_label = $geneHash{taxon_label} || '-';
#       my $bioentity_label = $geneHash{bioentity_label} || '-';
#       my $bioentity_name = $geneHash{bioentity_name} || '-';
#       my $entry = qq($bioentity_label ($taxon_label, $id, $bioentity_name));
#       $matches{$entry}++; 
#     }
#     if (scalar (@{ $jsonHash{"response"}{"docs"} }) >= $max_results) { $matches{"more results, type more to narrow your search"}++; }
#   
#   } # if (scalar keys %matches < $max_results)

#   $matches{'blah'}++;
#   $matches{'foo'}++;
#   $matches{'bar'}++;
#   my @tables = qw( prt_processname );
#   foreach my $table (@tables) {
#     my $result = $dbh->prepare( "SELECT * FROM $table WHERE LOWER($table) ~ '^$lcwords' ORDER BY $table;" );
# #     print qq( "SELECT * FROM $table WHERE LOWER($table) ~ '^$lcwords' ORDER BY $table;" <br/>);
#     $result->execute();
#     while ( (my @row = $result->fetchrow()) && (scalar keys %matches < $max_results) ) {
#       my $id = "WBProcess"; my $name = $row[1];
#       my $result2 = $dbh->prepare( "SELECT * FROM prt_processid WHERE joinkey = '$row[0]';" ); $result2->execute();
#       my @row2 = $result2->fetchrow(); $id = $row2[1];
#       $matches{"$name ( $id ) "}++;
#     }
#     $result = $dbh->prepare( "SELECT * FROM $table WHERE LOWER($table) ~ '$lcwords' AND LOWER($table) !~ '^$lcwords' ORDER BY $table;" );
#     $result->execute();
#     while ( (my @row = $result->fetchrow()) && (scalar keys %matches < $max_results) ) {
#       my $id = "WBProcess"; my $name = $row[1];
#       my $result2 = $dbh->prepare( "SELECT * FROM prt_processid WHERE joinkey = '$row[0]';" ); $result2->execute();
#       my @row2 = $result2->fetchrow(); $id = $row2[1];
#       $matches{"$name ( $id ) "}++; }
#     last if (scalar keys %matches >= $max_results);
#   } # foreach my $table (@tables)
#   if (scalar keys %matches >= $max_results) { $t->Replace($max_results - 1, 'no value', 'more results exist, type more to narrow your search'); }
  my $matches = join"\n", keys %matches;
#   my $matches = join"<br/>\n", keys %matches;
#   print qq(<br><br>MATCHES<br>);
  print $matches;
} # sub autocompleteGene

#           my $lcaHashref = &calculateLCA($ph1, $ph2);
#           my %lca = %$lcaHashref;
#   return \%lca;

sub solrSearch {
  my ($solr_gene_url, $matchesHashref, $max_results) = @_;
# print qq(S $solr_gene_url S<br/>\n);

#   my $matches = join"<br/>\n", keys %$matchesHashref;
#   print qq(<br>INSOLR MATCHES $matches<br>END INSOLR<br><br>);

  my $matchesCount = scalar keys %$matchesHashref;
  if ($matchesCount < $max_results) {
    my $page_data = get $solr_gene_url;
    unless ($page_data) { return $matchesHashref; }
    my $perl_scalar = $json->decode( $page_data );
    my %jsonHash = %$perl_scalar;

    foreach my $geneHash (@{ $jsonHash{"response"}{"docs"} }) {
      my %geneHash = %$geneHash;
#       my $id = $geneHash{bioentity_internal_id} || '-';
      my $id = $geneHash{id} || '-';
      my $synonym = '-';
      my $synonymRef = $geneHash{synonym} || '';
      if ($synonymRef) { 
        my (@syns) = @$synonymRef;
        $synonym = join ", ", @syns; }
      my $taxon_label = $geneHash{taxon_label} || '-';
      my $bioentity_label = $geneHash{bioentity_label} || '-';
      my $bioentity_name = $geneHash{bioentity_name} || '-';
      my $entry = qq($bioentity_label ($taxon_label, $id, $bioentity_name, $synonym));
      unless ($$matchesHashref{$entry}) { $$matchesHashref{$entry}++; }
    }
#     if (scalar (@{ $jsonHash{"response"}{"docs"} }) >= $max_results) { $$matchesHashref{"more results, type more to narrow your search"}++; }
    if (scalar (@{ $jsonHash{"response"}{"docs"} }) >= $max_results) { $$matchesHashref{"more results not shown; narrow your search"}++; }
  } # if (scalar keys %matches < $max_results)
  return $matchesHashref;
}


sub frontPage {
  print "Content-type: text/html\n\n";
  my $title = 'SObA pick a gene';
  my $header = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"><HTML><HEAD>';
  $header .= "<title>$title</title>\n";

  $header .= '<link rel="stylesheet" href="http://tazendra.caltech.edu/~azurebrd/stylesheets/jex.css" />';
  $header .= "<link rel=\"stylesheet\" type=\"text/css\" href=\"http://yui.yahooapis.com/2.7.0/build/autocomplete/assets/skins/sam/autocomplete.css\" />";

  $header .= "<style type=\"text/css\">#forcedPersonAutoComplete { width:25em; padding-bottom:2em; } .div-autocomplete { padding-bottom:1.5em; }</style>";
  $header .= qq(<style type="text/css">#forcedProcessAutoComplete { width:30em; padding-bottom:2em; } </style>);


  $header .= <<"EndOfText";
    <link rel="stylesheet" type="text/css" href="http://yui.yahooapis.com/2.7.0/build/autocomplete/assets/skins/sam/autocomplete.css" />
    <link rel="stylesheet" type="text/css" href="http://tazendra.caltech.edu/~azurebrd/stylesheets/jex.css" />
    <link rel="stylesheet" type="text/css" href="http://yui.yahooapis.com/2.7.0/build/fonts/fonts-min.css" />
    <script type="text/javascript" src="http://yui.yahooapis.com/2.7.0/build/yahoo-dom-event/yahoo-dom-event.js"></script>
    <script type="text/javascript" src="http://yui.yahooapis.com/2.7.0/build/connection/connection-min.js"></script>
    <script type="text/javascript" src="http://yui.yahooapis.com/2.7.0/build/datasource/datasource-min.js"></script>
    <script type="text/javascript" src="http://yui.yahooapis.com/2.7.0/build/autocomplete/autocomplete-min.js"></script>
    <script type="text/javascript" src="/~raymond/javascript/soba_biggo.js"></script>
EndOfText

#     <!-- always needed for yui -->
#     <script type="text/javascript" src="http://yui.yahooapis.com/2.7.0/build/yahoo-dom-event/yahoo-dom-event.js"></script>
# 
#     <!-- for autocomplete calls -->
#     <script type="text/javascript" src="http://yui.yahooapis.com/2.7.0/build/datasource/datasource-min.js"></script>
# 
#     <!-- OPTIONAL: Connection Manager (enables XHR for DataSource)      needed for Connect.asyncRequest -->
#     <script type="text/javascript" src="http://yui.yahooapis.com/2.7.0/build/connection/connection-min.js"></script>
# 
#     <!-- autocomplete js -->
#     <script type="text/javascript" src="http://yui.yahooapis.com/2.7.0/build/autocomplete/autocomplete-min.js"></script>

  $header .= "</head>";
  $header .= '<body class="yui-skin-sam">';
  print qq($header);

  print << "EndOfText";
    <B>Choose a gene <!--<span style="color: red;">*</span>--></B>
    <font size="-2" color="#3B3B3B">Start typing in a gene and choose from the drop-down.</font>
      <span id="containerForcedGeneAutoComplete">
        <div id="forcedGeneAutoComplete">
              <input size="50" name="gene" id="input_Gene" type="text" style="max-width: 444px; width: 99%; background-color: #E1F1FF;" value="">
              <div id="forcedGeneContainer"></div>
        </div></span><br/><br/>
  <br/>
EndOfText


  my $solr_taxon_url = 'http://wobr2.caltech.edu:8080/solr/biggo/select?qt=standard&fl=id,taxon,taxon_label&version=2.2&wt=json&rows=0&indent=on&q=*:*&facet=true&facet.field=taxon_label&facet.mincount=1&fq=document_category:%22bioentity%22';
  my $page_data = get $solr_taxon_url;
  my $perl_scalar = $json->decode( $page_data );
  my %jsonHash = %$perl_scalar;
  print qq(Prioritize search by selecting one or more species.<br/>\n);
  my %taxons;
#   print qq(<input type="checkbox" class="taxon_all" name="taxon_all" id="taxon_all" value="all" checked="checked">All Taxons</input><br/>\n);

  my @priorityTaxons = ( 'Homo sapiens', 'Arabidopsis thaliana', 'Caenorhabditis elegans', 'Danio rerio', 'Drosophila melanogaster', 'Escherichia coli K-12', 'Mus musculus', 'Rattus norvegicus', 'Saccharomyces cerevisiae S288c' );
  my %priorityTaxons;
  foreach my $taxon (@priorityTaxons) {
    $priorityTaxons{$taxon}++;
    my $taxon_plus = $taxon; $taxon_plus =~ s/ /+/g;
    print qq(<input type="checkbox" class="taxon" name="$taxon" id="$taxon" value="$taxon_plus" onclick="setAutocompleteListeners();">$taxon</input><br/>\n);
  }
  print qq(<br/>);
  print qq(<br/>Additional species.<br/>);

  while (scalar (@{ $jsonHash{"facet_counts"}{"facet_fields"}{"taxon_label"} }) > 0) {
    my $taxon      = shift @{ $jsonHash{"facet_counts"}{"facet_fields"}{"taxon_label"} };
    my $someNumber = shift @{ $jsonHash{"facet_counts"}{"facet_fields"}{"taxon_label"} };
    next if ($priorityTaxons{$taxon});	# already entered before
    my $taxon_plus = $taxon; $taxon_plus =~ s/ /+/g;
    $taxons{qq(<input type="checkbox" class="taxon" name="$taxon" id="$taxon" value="$taxon_plus" onclick="setAutocompleteListeners();">$taxon</input><br/>\n)}++;
  }
  foreach my $taxon (sort keys %taxons) {
    print $taxon;
  }


#   my $input_id = 'gene';
#   print qq(
#   <td id="td_AutoComplete_$input_id">
#   <div id="div_AutoComplete_$input_id" class="div-autocomplete">
#   <input size="40" id="$input_id" name="$input_id">
#   <div id="div_Container_$input_id"></div></div></td>);

#   my $data = '';
#   my $table = 'ATABLE';
#   my $order = '1';
#   my ($td_data) = &makeInputField($data, $table, $order, '3', '1', '');
#   print qq(<tr>$td_data</tr>);

  print qq(</body></html>);
} # sub frontPage

sub makeInputField {
  my ($current_value, $table, $order, $colspan, $rowspan, $class, $td_width, $input_size) = @_;
  unless ($current_value) { $current_value = ''; }
  my $freeForced = 'free';
  my $containerSpanId = "container${freeForced}${table}${order}AutoComplete";
  my $divAutocompleteId = "${freeForced}${table}${order}AutoComplete";
  my $inputId = "input_${table}_$order";
  my $divContainerId = "${freeForced}${table}${order}Container";
  my $data = "<td width=\"$td_width\" class=\"$class\" rowspan=\"$rowspan\" colspan=\"$colspan\">
  <span id=\"$containerSpanId\">
  <div id=\"$divAutocompleteId\" class=\"div-autocomplete\">
  <input id=\"$inputId\" name=\"$inputId\" size=\"$input_size\" value=\"$current_value\">
  <div id=\"$divContainerId\"></div></div></span>
  </td>";
#    <span id=\"container${freeForced}${table}AutoComplete\">
#    <div id=\"${freeForced}${table}AutoComplete\" class=\"div-autocomplete\">
#    <input id=\"input_$table\" name=\"input_$table\" size=\"$input_size\">
#    <div id=\"${freeForced}${table}Container\"></div></div></span>
  return $data;
} # sub makeInputField



sub autocompleteJqueryFixedsource {
  print <<"EndOfText";
Content-type: text/html\n
<!DOCTYPE html>
<html lang = "en">
   <head>
      <meta charset = "utf-8">
      <title>jQuery UI Autocomplete functionality</title>
      <link href = "https://code.jquery.com/ui/1.10.4/themes/ui-lightness/jquery-ui.css"
         rel = "stylesheet">
      <script src = "https://code.jquery.com/jquery-1.10.2.js"></script>
      <script src = "https://code.jquery.com/ui/1.10.4/jquery-ui.js"></script>
      
      <!-- Javascript -->
      <script>
         \$(function() {
            var availableTutorials  =  [
               "ActionScript",
               "Boostrap",
               "C",
               "C++",
            ];
            \$( "#automplete-1" ).autocomplete({
               source: availableTutorials
            });
         });
      </script>
   </head>
   
   <body>
      <!-- HTML --> 
      <div class = "ui-widget">
         <p>Enter a Gene</p>
         <label for = "automplete-1">Tags: </label>
         <input id = "automplete-1">
      </div>
   </body>
</html>
EndOfText
}

sub getSolrUrl {
  my ($focusTermId) = @_;
  my ($identifierType) = $focusTermId =~ m/^(\w+):/;
  my %idToSubdirectory;
  $idToSubdirectory{"WBbt"}        = "anatomy";
  $idToSubdirectory{"DOID"}        = "disease";
  $idToSubdirectory{"GO"}          = "go";
  $idToSubdirectory{"WBls"}        = "lifestage";
  $idToSubdirectory{"WBPhenotype"} = "phenotype";
  my $solr_url = $base_solr_url . '/';
#  my $solr_url = $base_solr_url . $idToSubdirectory{$identifierType} . '/';
} # sub getSolrUrl

sub getTopoHash {
  my ($focusTermId) = @_;
  my ($solr_url) = &getSolrUrl($focusTermId);
  my $url = $solr_url . "select?qt=standard&fl=*&version=2.2&wt=json&indent=on&rows=1&q=id:%22" . $focusTermId . "%22&fq=document_category:%22ontology_class%22";
  
  my $page_data = get $url;
  
  my $perl_scalar = $json->decode( $page_data );
  my %jsonHash = %$perl_scalar;

  my $topoHashref = $json->decode( $jsonHash{"response"}{"docs"}[0]{"topology_graph_json"} );
#   return ($topoHashref);
  my $transHashref = $json->decode( $jsonHash{"response"}{"docs"}[0]{"regulates_transitivity_graph_json"} );	# need this for inferred Tree View
  return ($topoHashref, $transHashref);
} # sub getTopoHash

sub getTopoChildrenParents {
  my ($focusTermId, $topoHref) = @_;
  my %topo = %$topoHref;
  my %children; 			# children of the wanted focusTermId, value is relationship type (predicate) ; are the corresponding nodes on an edge where the object is the focusTermId
  my %parents;				# direct parents of the wanted focusTermId, value is relationship type (predicate) ; are the corresponding nodes on an edge where the subject is the focusTermId
  my %child;				# for any term, each subkey is a child
  my (@edges) = @{ $topo{"edges"} };
  for my $index (0 .. @edges) {
    my ($sub, $obj, $pred) = ('', '', '');
    if ($edges[$index]{'sub'}) { $sub = $edges[$index]{'sub'}; }
    if ($edges[$index]{'obj'}) { $obj = $edges[$index]{'obj'}; }
    if ($edges[$index]{'pred'}) { $pred = $edges[$index]{'pred'}; }
    if ($obj eq $focusTermId) { $children{$sub} = $pred; }		# track children here
    if ($sub eq $focusTermId) { $parents{$obj}  = $pred; }		# track parents here
  }
  return (\%children, \%parents);
} # sub getTopoChildrenParents

sub calcNodeWidth {
  my ($nodeCount, $maxAnyCount) = @_;
  unless ($maxAnyCount) { $maxAnyCount = 1; }
  my $nodeWidth    = 1; my $nodeScale = 1.5; my $nodeMinSize = 0.01; my $logScaler = .6;
# $nodeWidth    = ( log($annotationCounts{$id}{'any'})/log($maxAnyCount) * $nodeScale ) + $nodeMinSize;
# $nodeWidth    = ( log(sqrt($annotationCounts{$id}{'any'}+$logScaler))/log(sqrt($maxAnyCount+$logScaler)) * $nodeScale ) + $nodeMinSize;
  $nodeWidth    = ( sqrt($nodeCount)/sqrt($maxAnyCount) * $nodeScale ) + $nodeMinSize;
  return $nodeWidth;
} # sub calcNodeWidth

sub getDiffTime {
  my ($start, $prev, $message) = @_;
  my $now = time;
  $now =~ s/(\....).*$/$1/;
  my $diffStart = $now - $startTime;
  $diffStart =~ s/(\....).*$/$1/;
  my $diffPrev  = $now - $prevTime;
  $diffPrev  =~ s/(\....).*$/$1/;
# print qq(START $start NOW $now PREV $prev DIFFPREV $diffPrev E<br/>);
  $prevTime = $now;
  $message = qq($diffStart seconds from start, $diffPrev seconds from previous check.  Now $message);
  return ($message);
} # sub getDiffTime




sub populateGeneNamesFromFlatfile {
  my %geneNameToId; my %geneIdToName;
  my $infile = '/home/azurebrd/cron/gin_names/gin_names.txt';
  open (IN, "<$infile") or die "Cannot open $infile : $!";
  while (my $line = <IN>) {
    chomp $line;
    my ($id, $name, $primary) = split/\t/, $line;
    if ($primary eq 'primary') { $geneIdToName{$id}     = $name; }
    my ($lcname)           = lc($name);
    $geneNameToId{$lcname} = $id; }
  close (IN) or die "Cannot close $infile : $!";
  return (\%geneNameToId, \%geneIdToName);
} # sub populateGeneNamesFromFlatfile

# sub populateGeneNamesFromPostgres {
#   my %geneNameToId; my %geneIdToName;
# #   my @tables = qw( gin_locus );
#   my @tables = qw( gin_wbgene gin_seqname gin_synonyms gin_locus );
# #   my @tables = qw( gin_seqname gin_synonyms gin_locus );
#   foreach my $table (@tables) {
#     my $result = $dbh->prepare( "SELECT * FROM $table;" );
#     $result->execute();
#     while (my @row = $result->fetchrow()) {
#       my $id                 = "WBGene" . $row[0];
#       my $name               = $row[1];
#       my ($lcname)           = lc($name);
#       $geneIdToName{$id}     = $name;
#       $geneNameToId{$lcname} = $id; } }
#   return (\%geneNameToId, \%geneIdToName);
# } # sub populateGeneNamesFromPostgres

sub calculateNodesAndEdges {
  my ($focusTermId, $datatype, $rootsChosen, $filterForLcaFlag) = @_;
  my (@parentNodes) = split/,/, $rootsChosen;
  unless ($datatype) { $datatype = 'phenotype'; }			# later will need to change based on different datatypes
  my ($var, $radio_iea)       = &getHtmlVar($query, 'radio_iea');
  my $toReturn = '';
#   my ($solr_url) = &getSolrUrl($focusTermId);
  my $solr_url = $base_solr_url;
    # link 1, from wbgene get wbphenotypes from   "grouped":{ "annotation_class":{ "matches":12, "ngroups":4, "groups":[{ "groupValue":"WBPhenotype:0000674", # }]}}

#   my $rootId = 'GO:0008150';
#   my $rootId = 'GO:0005575';
#   my $rootId = 'GO:0003674';
#   if ($datatype eq 'phenotype') { $rootId = 'GO:0008150'; }

  my %allLca;								# all nodes that are LCA to any pair of annotated terms
  my %nodes;
  my %edgesPtc;								# edges from parent to child

  my $nodeWidth    = 1;
  my $weightedNodeWidth    = 1;
  my $unweightedNodeWidth  = 1;
  my %annotationCounts;							# get annotation counts from evidence type
  my %phenotypes; my @annotPhenotypes;					# array of annotated terms to loop and do pairwise comparisons
#   my $annotation_count_solr_url = $solr_url . 'select?qt=standard&indent=on&wt=json&version=2.2&rows=100000&fl=regulates_closure,id,annotation_class&q=document_category:annotation&fq=-qualifier:%22not%22&fq=bioentity:%22WB:' . $focusTermId . '%22';	# for phenotype
  my $annotation_count_solr_url = $solr_url . 'select?qt=standard&indent=on&wt=json&version=2.2&rows=100000&fl=regulates_closure,id,annotation_class&q=document_category:annotation&fq=-qualifier:%22not%22&fq=bioentity:%22' . $focusTermId . '%22';
#   $toReturn .= qq(BAEARE $radio_iea RADIO_IEA<br>\n);
  if ($radio_iea eq 'radio_excludeiea') { $annotation_count_solr_url = $solr_url . 'select?qt=standard&indent=on&wt=json&version=2.2&rows=100000&fl=regulates_closure,id,annotation_class&q=document_category:annotation&fq=-qualifier:%22not%22&fq=-evidence_type:IEA&fq=bioentity:%22' . $focusTermId . '%22'; }
    elsif ($radio_iea eq 'radio_onlyiea') { $annotation_count_solr_url = $solr_url . 'select?qt=standard&indent=on&wt=json&version=2.2&rows=100000&fl=bioentity,regulates_closure,id,annotation_class&q=document_category:annotation&fq=-qualifier:%22not%22&fq=evidence_type:(IDA+IEP+IGC+IGI+IMP+IPI)&fq=bioentity:%22' . $focusTermId . '%22'; }
#   print qq($annotation_count_solr_url\n);
# 
# FOR DEBUGGING, DELETE LATER
# 
# http://wobr2.caltech.edu:8080/solr/biggo/select?qt=standard&indent=on&wt=json&version=2.2&rows=100000&fl=bioentity,regulates_closure,evidence_type,annotation_class&q=document_category:annotation&fq=-qualifier:%22not%22&fq=evidence_type:(IDA+IEP+IGC+IGI+IMP+IPI)&fq=bioentity:%22AspGD:ACLA_057430%22
# 
# http://wobr2.caltech.edu:8080/solr/biggo/select?qt=standard&indent=on&wt=json&version=2.2&rows=100000&fl=bioentity,regulates_closure,evidence_type,annotation_class&q=document_category:annotation&fq=-qualifier:%22not%22&fq=evidence_type:(IDA+IEP+IGC+IGI+IMP+IPI)&fq=bioentity:%22UniProtKB:O94905%22
# 
# http://wobr2.caltech.edu:8080/solr/biggo/select?qt=standard&indent=on&wt=json&version=2.2&rows=100000&fl=bioentity,regulates_closure,evidence_type,annotation_class&q=document_category:annotation&fq=-qualifier:%22not%22&fq=evidence_type:(IDA+IEP+IGC+IGI+IMP+IPI)&fq=bioentity:%22UniProtKB:O94905%22

  my $page_data   = get $annotation_count_solr_url;                                           # get the URL
  my $perl_scalar = $json->decode( $page_data );                        # get the solr data
  my %jsonHash    = %$perl_scalar;

  foreach my $doc (@{ $jsonHash{'response'}{'docs'} }) {
      my $phenotype = $$doc{'annotation_class'};
      $phenotypes{$phenotype}++;
      my $id = $$doc{'id'};
      my (@idarray) = split/\t/, $id;
      my $type = $idarray[6];
#       $annotationCounts{$phenotype}{'any'}++; $annotationCounts{$phenotype}{$type}++; 
#       $nodes{$phenotype}{'counts'}{'any'}++;  $nodes{$phenotype}{'counts'}{$type}++;  
      foreach my $goid (@{ $$doc{'regulates_closure'} }) {
        $annotationCounts{$goid}{'any'}++; $annotationCounts{$goid}{$type}++; 
        $nodes{$goid}{'counts'}{'any'}++;  $nodes{$goid}{'counts'}{$type}++;  } 

#       my $varCount = 0; my $rnaiCount = 0;
#       if ($id =~ m/WB:WBVar\d+/) {  my (@wbvar)  = $id =~ m/(WB:WBVar\d+)/g;  $varCount  = scalar @wbvar;  }
#       if ($id =~ m/WB:WBRNAi\d+/) { my (@wbrnai) = $id =~ m/(WB:WBRNAi\d+)/g; $rnaiCount = scalar @wbrnai; }
#       foreach my $phenotype (@{ $$doc{'regulates_closure'} }) {
#         if ($varCount) {  for (1 .. $varCount) {  $annotationCounts{$phenotype}{'any'}++; $annotationCounts{$phenotype}{'Allele'}++; 
#                                                   $nodes{$phenotype}{'counts'}{'any'}++;  $nodes{$phenotype}{'counts'}{'Allele'}++;  } }
#         if ($rnaiCount) { for (1 .. $rnaiCount) { $annotationCounts{$phenotype}{'any'}++; $annotationCounts{$phenotype}{'RNAi'}++;     
#                                                   $nodes{$phenotype}{'counts'}{'any'}++;  $nodes{$phenotype}{'counts'}{'RNAi'}++;    } }
#       }
  }

#   my $count = 0;
  foreach my $phenotypeId (sort keys %phenotypes) {
#     $count++;
#     last if ($count > 38);
    push @annotPhenotypes, $phenotypeId;
    my $phenotype_solr_url = $solr_url . 'select?qt=standard&fl=regulates_transitivity_graph_json,topology_graph_json&version=2.2&wt=json&indent=on&rows=1&fq=-is_obsolete:true&fq=document_category:%22ontology_class%22&q=id:%22' . $phenotypeId . '%22';

# print qq(S $phenotype_solr_url S<br/>\n);

    my $page_data   = get $phenotype_solr_url;                                           # get the URL
    my $perl_scalar = $json->decode( $page_data );                        # get the solr data
    my %jsonHash    = %$perl_scalar;
    next unless ($jsonHash{"response"}{"docs"}[0]{"regulates_transitivity_graph_json"} );	# term must have data to extra json from it
    my $transHashref = $json->decode( $jsonHash{"response"}{"docs"}[0]{"regulates_transitivity_graph_json"} );
    my %transHash = %$transHashref;
    my (@nodes)   = @{ $transHash{"nodes"} };
    my %transNodes;							# track transitivity nodes as nodes to keep from topology data
    for my $index (0 .. @nodes) { if ($nodes[$index]{'id'}) { my $id  = $nodes[$index]{'id'};  $transNodes{$id}++; } }

    my $topoHashref = $json->decode( $jsonHash{"response"}{"docs"}[0]{"topology_graph_json"} );
    my %topoHash = %$topoHashref;
    my (@edges)   = @{ $topoHash{"edges"} };
    for my $index (0 .. @edges) {                                       # for each edge, add to graph
      my ($sub, $obj, $pred) = ('', '', '');                            # subject object predicate from topology_graph_json
      if ($edges[$index]{'sub'}) {  $sub  = $edges[$index]{'sub'};  }
      if ($edges[$index]{'obj'}) {  $obj  = $edges[$index]{'obj'};  }
      next unless ( ($transNodes{$sub}) && ($transNodes{$obj}) );
      if ($edges[$index]{'pred'}) { $pred = $edges[$index]{'pred'}; }
      my $direction = 'back'; my $style = 'solid';                      # graph arror direction and style
      if ($sub && $obj && $pred) {                                      # if subject + object + predicate
        $edgesAll{$phenotypeId}{$sub}{$obj}++;				# for an annotated term's edges, each child to its parents
        $edgesPtc{$obj}{$sub}++;					# any existing edge, parent to child
      } # if ($sub && $obj && $pred)
    } # for my $index (0 .. @edges)
    my (@nodes)   = @{ $topoHash{"nodes"} };
    for my $index (0 .. @nodes) {                                       # for each node, add to graph
      my ($id, $lbl) = ('', '');                                        # id and label
      if ($nodes[$index]{'id'}) {  $id  = $nodes[$index]{'id'};  }
      if ($nodes[$index]{'lbl'}) { $lbl = $nodes[$index]{'lbl'}; }
      next unless ($id);
# UNDO THIS
      $lbl = "$id - $lbl";                                          # node label should have full id, not stripped of :, which is required for edge title text
      $nodes{$id}{label} = $lbl;
      next unless ($transNodes{$id});
#       $lbl =~ s/ /<br\/>/g;                                                # replace spaces with html linebreaks in graph for more-square boxes
      my $label = "$lbl";                                          # node label should have full id, not stripped of :, which is required for edge title text
      if ($annotationCounts{$id}) { 					# if there are annotation counts to variation and/or rnai, add them to the box
        my @annotCounts;
        foreach my $evidenceType (sort keys %{ $annotationCounts{$id} }) {
          next if ($evidenceType eq 'any');				# skip 'any', only used for relative size to max value
          push @annotCounts, qq($annotationCounts{$id}{$evidenceType} $evidenceType); }
        my $annotCounts = join"; ", @annotCounts;
        $label = qq(LINEBREAK<br\/>$label<br\/><font color="transparent">$annotCounts<\/font>);				# add html line break and annotation counts to the label
      }
      if ($id && $lbl) { 
        $nodesAll{$phenotypeId}{$id} = $lbl;
      }
    }
  } # foreach my $phenotypeId (sort keys %phenotypes)

  if (!$filterForLcaFlag) {
     foreach my $annotTerm (sort keys %nodesAll) {
       $nodes{$annotTerm}{annot}++;
       foreach my $phenotype (sort keys %{ $nodesAll{$annotTerm} }) {
         my $url = "http://www.wormbase.org/species/all/go_term/$phenotype";                              # URL to link to wormbase page for object
           $allLca{$phenotype}++;
           unless ($phenotypes{$phenotype}) { 					# only add lca nodes that are not annotated terms
             $nodes{$phenotype}{lca}++; } } } }
    else {
      while (@annotPhenotypes) {
        my $ph1 = shift @annotPhenotypes;					# compare each annotated term node to all other annotated term nodes
        my $url = "http://www.wormbase.org/species/all/go_term/$ph1";                              # URL to link to wormbase page for object
        my $xlabel = $ph1; 	# FIX
        $nodes{$ph1}{annot}++;
        foreach my $ph2 (@annotPhenotypes) {				# compare each annotated term node to all other annotated term nodes
          my $lcaHashref = &calculateLCA($ph1, $ph2);
          my %lca = %$lcaHashref;
          foreach my $lca (sort keys %lca) {
            $url = "http://www.wormbase.org/species/all/go_term/$lca";                              # URL to link to wormbase page for object
            $allLca{$lca}++;
            unless ($phenotypes{$lca}) { 					# only add lca nodes that are not annotated terms
              $xlabel = $lca; 					# FIX
              $nodes{$lca}{lca}++;
            }
          } # foreach my $lca (sort keys %lca)
        } # foreach my $ph2 (@annotPhenotypes)				# compare each annotated term node to all other annotated term nodes
      } # while (@annotPhenotypes)
    }

  my %edgesLca;								# edges that exist in graph generated from annoated terms + lca terms + root

#   my @parentNodes = ($rootId);						# nodes that are parents, at first root, later any nodes that should be in graph
#   my @parentNodes = ('GO:0008150', 'GO:0005575', 'GO:0003674');
#   my @parentNodes = ('GO:0008150');					# cannot compute to fake root, edges LCA creates wrong edges going to fake root from other terms, like GO:0005622 to fake root for WBGene0000899
  while (@parentNodes) {						# while there are parent nodes, go through them
    my $parent = shift @parentNodes;					# take a parent
    my %edgesPtcCopy = %{ dclone(\%edgesPtc) };				# make a temp copy since edges will be getting deleted per parent
    while (scalar keys %{ $edgesPtcCopy{$parent} } > 0) {		# while parent has children
      foreach my $child (sort keys %{ $edgesPtcCopy{$parent} }) {	# each child of parent
        if ($allLca{$child} || $phenotypes{$child}) { 			# good node, keep edge when child is an lca or annotated term
            delete $edgesPtcCopy{$parent}{$child};			# remove from %edgesPtc, does not need to be checked further
            push @parentNodes, $child;					# child is a good node, add to parent list to check its children
# print qq(EDGES LCA PARENT $parent CHILD $child E<br/>\n);
            $edgesLca{$parent}{$child}++; }				# add parent-child edge to final graph
          else {							# bad node, remove and reconnect edges
            delete $edgesPtcCopy{$parent}{$child};			# remove parent-child edge
            foreach my $grandchild (sort keys %{ $edgesPtcCopy{$child} }) {	# take each grandchild of child
              delete $edgesPtcCopy{$child}{$grandchild};		# remove child-grandchild edge
              $edgesPtcCopy{$parent}{$grandchild}++; } }		# make replacement edge between parent and grandchild
      } # foreach my $child (sort keys %{ $edgesPtcCopy{$parent} })
    } # while (scalar keys %{ $edgesPtcCopy{$parent} } > 0)
  } # while (@parentNodes)
  foreach my $parent (sort keys %edgesLca) {
    my $parent_placeholder = $parent;
    $parent_placeholder =~ s/:/_placeholderColon_/g;                                  # edges won't have proper title text if ids have : in them
    foreach my $child (sort keys %{ $edgesLca{$parent} }) {
      my $child_placeholder = $child;
      $child_placeholder =~ s/:/_placeholderColon_/g;                                  # edges won't have proper title text if ids have : in them
#       $toReturn .= qq(EDGE $parent TO $child E<br/>\n);
#       $gviz_lca_edges->add_edge(from => "$parent_placeholder", to => "$child_placeholder", dir => "$direction", color => "$edgecolor", fontcolor => "$edgecolor", style => "$style", arrowsize => ".3"); 
#       $gviz_lca_unweighted->add_edge(from => "$parent_placeholder", to => "$child_placeholder", dir => "$direction", color => "$edgecolor", fontcolor => "$edgecolor", style => "$style", arrowsize => ".3"); 
#       $gviz_homogeneous->add_edge(from => "$parent_placeholder", to => "$child_placeholder", dir => "$direction", color => "$edgecolor", fontcolor => "$edgecolor", style => "$style", arrowsize => ".3"); 
    } # foreach my $child (sort keys %{ $edgesLca{$parent} })
  } # foreach my $parent (sort keys %edgesLca)

#   foreach my $node (sort keys %nodes) {
#     if ($nodes{$node}{annot}) {    $toReturn .= qq($node annot<br/>); }
#       elsif ($nodes{$node}{lca}) { $toReturn .= qq($node lca<br/>); }
#   }
  return ($toReturn, \%nodes, \%edgesLca);
} # sub calculateNodesAndEdges


sub annotSummaryJsonp {
# http://wobr2.caltech.edu/~azurebrd/cgi-bin/amigo.cgi?action=annotSummaryJsonp&focusTermId=WBGene00000899
#   print qq(Content-type: application/json\n\n);	# this was for json
# for cross domain access, needs to be jsonp with header below, content-type is different, json has a function wrapped around it.
  print $query->header(
    -type => 'application/javascript',
    -access_control_allow_origin => '*',
  );
  &annotSummaryJsonCode();
} # sub annotSummaryJsonp

sub annotSummaryJson {			# temporarily keep this for the live www.wormbase going through the fake phenotype_graph_json widget
# http://wobr2.caltech.edu/~azurebrd/cgi-bin/amigo.cgi?action=annotSummaryJson&focusTermId=WBGene00000899
  print qq(Content-type: application/json\n\n);	# this was for json
  &annotSummaryJsonCode();
} # sub annotSummaryJson

sub annotSummaryJsonCode {
  my ($var, $focusTermId)       = &getHtmlVar($query, 'focusTermId');
  my ($var, $datatype)          = &getHtmlVar($query, 'datatype');
  my ($var, $fakeRootFlag)      = &getHtmlVar($query, 'fakeRootFlag');
  my ($var, $filterLongestFlag) = &getHtmlVar($query, 'filterLongestFlag');
  my ($var, $filterForLcaFlag)  = &getHtmlVar($query, 'filterForLcaFlag');
  my ($var, $rootsChosen)       = &getHtmlVar($query, 'rootsChosen');
  my (@rootsChosen) = split/,/, $rootsChosen;
  my ($return, $nodesHashref, $edgesLcaHashref) = &calculateNodesAndEdges($focusTermId, $datatype, $rootsChosen, $filterForLcaFlag);
  if ($return) { print qq(RETURN $return ENDRETURN\n); }
  my %nodes    = %$nodesHashref;
  my %edgesLca = %$edgesLcaHashref;
  if ($fakeRootFlag) { 
    my $fakeRoot = 'GO:0000000';
    $nodes{$fakeRoot}{label} = 'Gene Ontology';
    $nodesAll{$fakeRoot}{label} = 'Gene Ontology';
    foreach my $sub (@rootsChosen) {
      $edgesLca{$fakeRoot}{$sub}++;					# any existing edge, parent to child 
#     my @branchNodes = ('GO:0008150', 'GO:0005575', 'GO:0003674');
#     foreach my $sub (@branchNodes) {
#       $edgesLca{$fakeRoot}{$sub}++;					# any existing edge, parent to child
#   print qq(EDGES LCA fr $fakeRoot S $sub E<br/>\n);
  } }
  my @nodes = ();
  my %rootNodes; 
#   $rootNodes{'GO:0008150'}++; $rootNodes{'GO:0005575'}++; $rootNodes{'GO:0003674'}++; 
  foreach my $root (@rootsChosen) { $rootNodes{$root}++; }
  if ($fakeRootFlag) { $rootNodes{'GO:0000000'}++; }
  my $rootNode = 'GO:0008150';
#   my $rootNode = 'GO:0005575';
#   my $rootNode = 'GO:0003674';
  my $diameterMultiplier = 60;

  my %edgesFromLongest;							# find edges that belong to the longest path from all nodes to each of their children (to remove indirect nodes, like a grandchild directly to the grandparent, bypassing the parent)
#   foreach my $source (@rootsChosen)
  foreach my $source (sort keys %nodes) {				# for all nodes, calculate longest paths to each child and add to %edgesFromLongest
    foreach my $target (sort keys %{ $edgesLca{$source } }) {
#       print qq(ROOT $source TO $target E\n);
      %paths = ();
      foreach my $source (sort keys %edgesLca) {
        foreach my $target (sort keys %{ $edgesLca{$source } }) {
          $paths{"childToParent"}{$target}{$source}++; } }
      my ($edgesFromFinalPathHashref) = &getLongestPathAndTransitivity($source, $target);
      my %edgesFromFinalPath = %$edgesFromFinalPathHashref;
      foreach my $source (sort keys %{ $edgesFromFinalPath{'longest'} }) {
        foreach my $target (sort keys %{ $edgesFromFinalPath{'longest'}{$source} }) {
# print qq(EFILTERED $source TO $target E\n);
          $edgesFromLongest{$source}{$target}++; } }
    } # foreach my $target (sort keys %{ $edgesLca{$source } })
  } # foreach my $source (@rootsChosen)

  my @edges = ();
  my %nodesWithEdges;
  foreach my $source (sort keys %edgesLca) {
    foreach my $target (sort keys %{ $edgesLca{$source } }) {
      if ( ($filterLongestFlag) && !($edgesFromLongest{$target}{$source}) ) { next; }
#       next unless ($edgesFromLongest{$target}{$source});			# only show edges that belong in longest path for some relationship
      my $lineColor = '#ddd'; if ($source eq 'GO:0000000') { $lineColor = '#fff'; }
      my $cSource = $source; $cSource =~ s/GO://;
      my $cTarget = $target; $cTarget =~ s/GO://;
      $nodesWithEdges{"GO:$cSource"}++; $nodesWithEdges{"GO:$cTarget"}++;
      my $name = $cSource . $cTarget;
# print qq(SOURCE $cSource TARGET $cTarget END<br/>\n);
      push @edges, qq({ "data" : { "id" : "$name", "weight" : 1, "source" : "$cSource", "target" : "$cTarget", "lineColor" : "$lineColor" } }); } }
#   push @edges, qq({ "data" : { "id" : "legend_nodirect_legend_yesdirect", "weight" : 1, "source" : "legend_nodirect", "target" : "legend_yesdirect" } });
#   push @edges, qq({ "data" : { "id" : "legend_root_legend_nodirect", "weight" : 1, "source" : "legend_root", "target" : "legend_nodirect" } });
#   push @edges, qq({ "data" : { "id" : "legend_legend_legend_root", "weight" : 1, "source" : "legend_legend", "target" : "legend_root" } });
  my $edges = join",\n", @edges; 

  my ($goslimIdsRef) = &getGoSlimGoids();
  my %goslimIds = %$goslimIdsRef;

  foreach my $node (sort keys %nodes) {
    next unless ($nodesWithEdges{$node});
    my $name = $nodes{$node}{label};
# print qq(NODE $node NAME $name END<br/>\n);
    $name =~ s/ /\\n/g;
    my @annotCounts;
    foreach my $evidenceType (sort keys %{ $nodes{$node}{'counts'} }) {
      next if ($evidenceType eq 'any');				# skip 'any', only used for relative size to max value
#       my $annotationCount = $nodes{$node}{'counts'}{$evidenceType}; my $type = $evidenceType;
#       if ($annotationCount > 1) { $type .= 's'; }
#       push @annotCounts, qq($annotationCount $type);
      push @annotCounts, qq($nodes{$node}{'counts'}{$evidenceType} $evidenceType); }
    my $annotCounts = join"; ", @annotCounts;
    my $diameter = $diameterMultiplier * &calcNodeWidth($nodes{$node}{'counts'}{'any'}, $nodes{"$rootNode"}{'counts'}{'any'});
    my $diameter_unweighted = 40;
    my $diameter_weighted = $diameter;
    my $fontSize = $diameter * .2; if ($fontSize < 4) { $fontSize = 4; }
    my $fontSize_weighted = $fontSize;
    my $fontSize_unweighted = 6;
    my $borderWidth = 2; 
    my $borderWidth_weighted = $borderWidth;
    my $borderWidth_unweighted = 2;				# scaled diameter and fontSize to keep borderWidth the same, but passing values in case we ever want to change them, we won't have to change the cytoscape receiving the json
    my $borderWidthRoot = 8; 
    my $borderWidthRoot_weighted = 4 * $borderWidth;
    my $borderWidthRoot_unweighted = 8;				# scaled diameter and fontSize to keep borderWidth the same, but passing values in case we ever want to change them, we won't have to change the cytoscape receiving the json
    my $labelColor = 'black'; if ($node eq 'GO:0000000') { $labelColor = '#fff'; }
    my $backgroundColor = 'white'; 
    if ($rootNodes{$node}) {
      my $nodeColor  = 'blue';  if ($node eq 'GO:0000000') { $nodeColor  = '#fff'; }
      if ($goslimIds{$node}) { $backgroundColor = $nodeColor; }
# print qq(ROOT NODE $node\n);
  $node =~ s/GO://; push @nodes, qq({ "data" : { "id" : "$node", "name" : "$name", "annotCounts" : "$annotCounts", "borderStyle" : "dashed", "labelColor" : "$labelColor", "nodeColor" : "$nodeColor", "borderWidthUnweighted" : "$borderWidthRoot_unweighted", "borderWidthWeighted" : "$borderWidthRoot_weighted", "borderWidth" : "$borderWidthRoot", "fontSizeUnweighted" : "$fontSize_unweighted", "fontSizeWeighted" : "$fontSize_weighted", "fontSize" : "$fontSize", "diameter" : $diameter, "diameter_weighted" : $diameter_weighted, "diameter_unweighted" : $diameter_unweighted, "backgroundColor" : "$backgroundColor", "nodeShape" : "rectangle" } }); }
      elsif ($nodes{$node}{lca}) {
# print qq(LCA NODE $node\n);
           if ($goslimIds{$node}) { $backgroundColor = 'blue'; }
           $node =~ s/GO://; push @nodes, qq({ "data" : { "id" : "$node", "name" : "$name", "annotCounts" : "$annotCounts", "borderStyle" : "dashed", "labelColor" : "$labelColor", "nodeColor" : "blue", "borderWidthUnweighted" : "$borderWidth_unweighted", "borderWidthWeighted" : "$borderWidth_weighted", "borderWidth" : "$borderWidth", "fontSizeUnweighted" : "$fontSize_unweighted", "fontSizeWeighted" : "$fontSize_weighted", "fontSize" : "$fontSize", "diameter" : $diameter, "diameter_weighted" : $diameter_weighted, "diameter_unweighted" : $diameter_unweighted, "backgroundColor" : "$backgroundColor", "nodeShape" : "ellipse" } });   }
      elsif ($nodes{$node}{annot}) {
# print qq(ANNOT NODE $node\n);
         if ($goslimIds{$node}) { $backgroundColor = 'red'; }
         $node =~ s/GO://; push @nodes, qq({ "data" : { "id" : "$node", "name" : "$name", "annotCounts" : "$annotCounts", "borderStyle" : "solid", "labelColor" : "$labelColor", "nodeColor" : "red", "borderWidthUnweighted" : "$borderWidth_unweighted", "borderWidthWeighted" : "$borderWidth_weighted", "borderWidth" : "$borderWidth", "fontSizeUnweighted" : "$fontSize_unweighted", "fontSizeWeighted" : "$fontSize_weighted", "fontSize" : "$fontSize", "diameter" : $diameter, "diameter_weighted" : $diameter_weighted, "diameter_unweighted" : $diameter_unweighted, "backgroundColor" : "$backgroundColor", "nodeShape" : "ellipse" } });     } 
      else {
# print qq(OTHER NODE $node\n); 
    }
  }

  unless (scalar @nodes > 0) { push @nodes, qq({ "data" : { "id" : "0000000", "name" : "Gene\nOntology", "annotCounts" : "", "borderStyle" : "dashed", "labelColor" : "#888", "nodeColor" : "#888", "borderWidthUnweighted" : "8", "borderWidthWeighted" : "8", "borderWidth" : "8", "fontSizeUnweighted" : "6", "fontSizeWeighted" : "4", "fontSize" : "4", "diameter" : 0.6, "diameter_weighted" : 0.6, "diameter_unweighted" : 40, "nodeShape" : "rectangle" } }); }

  my $nodes = join",\n", @nodes; 
  print qq({ "elements" : {\n);
  print qq("nodes" : [\n);
  print qq($nodes\n);
  print qq(],\n);
  print qq("edges" : [\n);
  print qq($edges\n);
  print qq(]\n);
  print qq(} }\n);
} # sub annotSummaryJsonCode

sub getGoSlimGoids {
  my %goslimIds;
  my $goslimUrl = 'http://wobr2.caltech.edu:8080/solr/biggo/select?qt=standard&fl=id,annotation_class_label,topology_graph_json,subset&version=2.2&wt=json&indent=on&rows=1000&q=*:*&fq=document_category:%22ontology_class%22&fq=subset:%22goslim_agr%22';
  my $goslimData = get $goslimUrl;
  my $perl_scalar = $json->decode( $goslimData );
  my %goslimHash = %$perl_scalar;
  foreach my $entry (@{ $goslimHash{"response"}{"docs"} }) {
    my $goid        = $$entry{'id'};
    my $goname      = $$entry{'annotation_class_label'};
    $goslimIds{$goid} = $goname;
  }
  return \%goslimIds;
} # sub getGoSlimGoids

sub annotSummaryCytoscape {
# http://wobr2.caltech.edu/~azurebrd/cgi-bin/amigo.cgi?action=annotSummaryCytoscape&focusTermId=WBGene00000899
  my ($all_roots) = @_;
  my ($var, $focusTermId)          = &getHtmlVar($query, 'focusTermId');
  ($var, my $autocompleteValue)    = &getHtmlVar($query, 'autocompleteValue');
  ($var, my $datatype)             = &getHtmlVar($query, 'datatype');
  ($var, my $showControlsFlag)     = &getHtmlVar($query, 'showControlsFlag');
  ($var, my $fakeRootFlag)         = &getHtmlVar($query, 'fakeRootFlag');
  ($var, my $filterLongestFlag)    = &getHtmlVar($query, 'filterLongestFlag');
  ($var, my $filterForLcaFlag)     = &getHtmlVar($query, 'filterForLcaFlag');
  ($var, my $nodeCountFlag)        = &getHtmlVar($query, 'nodeCountFlag');
  ($var, my $radio_iea)            = &getHtmlVar($query, 'radio_iea');
  ($var, my $root_bp)              = &getHtmlVar($query, 'root_bp');
  ($var, my $root_mf)              = &getHtmlVar($query, 'root_mf');
  ($var, my $root_cc)              = &getHtmlVar($query, 'root_cc');
  my $toPrint = ''; my $return = '';
  my $checked_radio_withiea = 'checked="checked"'; my $checked_radio_excludeiea = ''; my $checked_radio_onlyiea = '';
  if ($radio_iea eq 'radio_excludeiea') { $checked_radio_withiea = ''; $checked_radio_excludeiea = 'checked="checked"'; }
    elsif ($radio_iea eq 'radio_onlyiea') { $checked_radio_withiea = ''; $checked_radio_onlyiea = 'checked="checked"'; }
  my $checked_root_bp = ''; my $checked_root_cc = ''; my $checked_root_mf = ''; 
  my @roots;
  if ($all_roots eq 'all_roots') { 
      $fakeRootFlag = 1; $filterLongestFlag = 1; $filterForLcaFlag = 1;
      push @roots, "GO:0008150"; push @roots, "GO:0005575"; push @roots, "GO:0003674";
      $checked_root_bp = 'checked="checked"'; $checked_root_cc = 'checked="checked"'; $checked_root_mf = 'checked="checked"'; }
    else {
      if ($root_bp) { $checked_root_bp = 'checked="checked"'; push @roots, $root_bp; }
      if ($root_cc) { $checked_root_cc = 'checked="checked"'; push @roots, $root_cc; }
      if ($root_mf) { $checked_root_mf = 'checked="checked"'; push @roots, $root_mf; } }
  my $roots = join",", @roots;

  unless ($focusTermId) {
    ($focusTermId) = $autocompleteValue =~ m/, (.*?),/;
  }

  my $goslimButtons = 'AGR Slim terms in graph:<br/>';
  my ($goslimIdsRef) = &getGoSlimGoids();
  my %goslimIds = %$goslimIdsRef;
  foreach my $goid (sort keys %goslimIds) {
    my $goname = $goslimIds{$goid};
    $goid =~ s/GO://;
    my $button      = qq(<span id="$goid" style="display: none">- $goname<br/></span>);
#     my $button      = qq(<button id="$goid" style="display: none">$goname</button>);
#     my $button      = qq(<button id="$goid" style="display: none">$goid - $goname</button>);
    $goslimButtons .= qq($button);
  } # foreach my $goid (sort keys %goslimIds)

#   my $goslimUrl = 'http://wobr2.caltech.edu:8080/solr/biggo/select?qt=standard&fl=id,annotation_class_label,topology_graph_json,subset&version=2.2&wt=json&indent=on&rows=1000&q=*:*&fq=document_category:%22ontology_class%22&fq=subset:%22goslim_agr%22';
#   my $goslimData = get $goslimUrl;
#   my $perl_scalar = $json->decode( $goslimData );
#   my %goslimHash = %$perl_scalar;
#   foreach my $entry (@{ $goslimHash{"response"}{"docs"} }) {
#     my $goid        = $$entry{'id'};
#     $goid =~ s/GO://;
#     my $goname      = $$entry{'annotation_class_label'};
#     my $button      = qq(<button id="$goid" style="display: none">$goid - $goname</button>);
# #     my $button      = qq(<input type="checkbox" id="$goid">$goid - $goname</input>);
#     $goslimButtons .= qq($button);
# #   foreach my $geneHash (@{ $jsonHash{"response"}{"docs"} }) {
# #     my %geneHash = %$geneHash;
# #     my $id = $geneHash{id} || '-';
#   }

#   my $jsonUrl = 'http://wobr2.caltech.edu/~azurebrd/wbgene00000899b.json';
#   my $jsonUrl = 'http://wobr2.caltech.edu/~azurebrd/cgi-bin/amigo.cgi?action=annotSummaryJson&focusTermId=' . $focusTermId;
  my $jsonUrl = 'soba_biggo.cgi?action=annotSummaryJson&focusTermId=' . $focusTermId . '&radio_iea=' . $radio_iea . '&rootsChosen=' . $roots;
  unless ($showControlsFlag) { $showControlsFlag = 0; }
  $jsonUrl .= "&showControlsFlag=$showControlsFlag";
  unless ($fakeRootFlag) { $fakeRootFlag = 0; }
  $jsonUrl .= "&fakeRootFlag=$fakeRootFlag";
  unless ($filterForLcaFlag) { $filterForLcaFlag = 0; }
  $jsonUrl .= "&filterForLcaFlag=$filterForLcaFlag";
  unless ($filterLongestFlag) { $filterLongestFlag = 0; }
  $jsonUrl .= "&filterLongestFlag=$filterLongestFlag";
  my $checked_showControls = ''; my $checked_fakeRoot = ''; my $checked_filterLca = ''; my $checked_filterLongest = ''; my $checked_nodeCount = '';
  my $displayControlMenu = 'none';		# by default don't show controls
  if ($showControlsFlag) {
    $displayControlMenu = '';			# show controls if checked on
    $checked_showControls  = 'checked="checked"'; }
  if ($nodeCountFlag) {     $checked_nodeCount     = 'checked="checked"'; }
  if ($fakeRootFlag) {      $checked_fakeRoot      = 'checked="checked"'; }
  if ($filterForLcaFlag) {  $checked_filterLca     = 'checked="checked"'; }
  if ($filterLongestFlag) { $checked_filterLongest = 'checked="checked"'; }
  my $show_node_count = 'none';
  if ($nodeCountFlag)     { $show_node_count = ''; }
  print << "EndOfText";
Content-type: text/html\n
<!DOCTYPE html>
<html>
<head>
<link href="http://wobr2.caltech.edu/~azurebrd/work/cytoscape/style.css" rel="stylesheet" />
<link href="http://cdnjs.cloudflare.com/ajax/libs/qtip2/2.2.0/jquery.qtip.min.css" rel="stylesheet" type="text/css" />
<meta charset=utf-8 />
<meta name="viewport" content="user-scalable=no, initial-scale=1.0, minimum-scale=1.0, maximum-scale=1.0, minimal-ui">
<title>$focusTermId Cytoscape view</title>


<script src="http://code.jquery.com/jquery-2.0.3.min.js"></script>

<script src="http://wobr2.caltech.edu/~azurebrd/javascript/cytoscape.min.js"></script>

<script src="http://wobr2.caltech.edu/~azurebrd/javascript/dagre.min.js"></script>
<script src="https://cdn.rawgit.com/cytoscape/cytoscape.js-dagre/1.1.2/cytoscape-dagre.js"></script>

<script src="http://cdnjs.cloudflare.com/ajax/libs/qtip2/2.2.0/jquery.qtip.min.js"></script>
<script src="https://cdn.rawgit.com/cytoscape/cytoscape.js-qtip/2.2.5/cytoscape-qtip.js"></script>

<script type="text/javascript">
\$(function(){

//   var elesJson = {
//     nodes: [
//       { data: { id: 'a', foo: 3, bar: 5, baz: 7 } },
//       { data: { id: 'b', foo: 7, bar: 1, baz: 3 } },
//       { data: { id: 'c', foo: 2, bar: 7, baz: 6 } },
//       { data: { id: 'd', foo: 9, bar: 5, baz: 2 } },
//       { data: { id: 'e', foo: 2, bar: 4, baz: 5 } }
//     ],
//   
//     edges: [
//       { data: { id: 'ae', weight: 1, source: 'a', target: 'e' } },
//       { data: { id: 'ab', weight: 3, source: 'a', target: 'b' } },
//       { data: { id: 'be', weight: 4, source: 'b', target: 'e' } },
//       { data: { id: 'bc', weight: 5, source: 'b', target: 'c' } },
//       { data: { id: 'ce', weight: 6, source: 'c', target: 'e' } },
//       { data: { id: 'cd', weight: 2, source: 'c', target: 'd' } },
//       { data: { id: 'de', weight: 7, source: 'd', target: 'e' } }
//     ]
//   };
// 
//   \$('#cy2').cytoscape({
//     style: cytoscape.stylesheet()
//       .selector('node')
//         .css({
//           'background-color': '#6272A3',
//           'shape': 'rectangle',
//           'width': 'mapData(foo, 0, 10, 10, 30)',
//           'height': 'mapData(bar, 0, 10, 10, 50)',
//           'content': 'data(id)'
//         })
//       .selector('edge')
//         .css({
//           'width': 'mapData(weight, 0, 10, 3, 9)',
//           'line-color': '#B1C1F2',
//           'target-arrow-color': '#B1C1F2',
//           'target-arrow-shape': 'triangle',
//           'opacity': 0.8
//         })
//       .selector(':selected')
//         .css({
//           'background-color': 'black',
//           'line-color': 'black',
//           'target-arrow-color': 'black',
//           'source-arrow-color': 'black',
//           'opacity': 1
//         }),
// 
//     elements: elesJson,
// 
//     layout: {
//       name: 'breadthfirst',
//       directed: true,
//       padding: 10
//     },
// 
//     ready: function(){
//       // ready 2
//     }
//   });


  // get exported json from cytoscape desktop via ajax
  var graphP = \$.ajax({
    url: '$jsonUrl',
    type: 'GET',
    dataType: 'json'
  });

  Promise.all([ graphP ]).then(initCy);

  function initCy( then ){
    var elements = then[0].elements;
    \$('#controldiv').show(); \$('#loadingdiv').hide();	// show controls and hide loading when graph loaded
    var cyPhenGraph = window.cyPhenGraph = cytoscape({
      container: document.getElementById('cyPhenGraph'),
      layout: { name: 'dagre', padding: 10, nodeSep: 5 },
      style: cytoscape.stylesheet()
        .selector('node')
          .css({
            'content': 'data(name)',
            'background-color': 'data(backgroundColor)',
            'color': 'data(labelColor)',
            'shape': 'data(nodeShape)',
            'border-color': 'data(nodeColor)',
            'border-style': 'data(borderStyle)',
            'border-width': 'data(borderWidth)',
            'width': 'data(diameter)',
            'height': 'data(diameter)',
            'text-valign': 'center',
            'text-wrap': 'wrap',
            'min-zoomed-font-size': 8,
            'border-opacity': 0.3,
            'background-opacity': 0.3,
            'font-size': 'data(fontSize)'
          })
        .selector('edge')
          .css({
            'target-arrow-shape': 'none',
            'source-arrow-shape': 'triangle',
            'width': 2,
            'line-color': 'data(lineColor)',
            'target-arrow-color': 'data(lineColor)',
            'source-arrow-color': 'data(lineColor)'
          })
        .selector('.highlighted')
          .css({
            'background-color': '#61bffc',
            'line-color': '#61bffc',
            'target-arrow-color': '#61bffc',
            'transition-property': 'background-color, line-color, target-arrow-color',
            'transition-duration': '0.5s'
          })
        .selector('.faded')
          .css({
            'opacity': 0.25,
            'text-opacity': 0
          }),
      elements: elements,
      wheelSensitivity: 0.2,
    
      ready: function(){
        window.cyPhenGraph = this;
        cyPhenGraph.elements().unselectify();
        
        cyPhenGraph.on('tap', 'node', function(e){
          var node = e.cyTarget; 
          var nodeId   = node.data('id');
          var neighborhood = node.neighborhood().add(node);
          cyPhenGraph.elements().addClass('faded');
          neighborhood.removeClass('faded');

          var node = e.cyTarget;
          var nodeId   = node.data('id');
          var nodeName = node.data('name');
          var annotCounts = node.data('annotCounts');
//           var qtipContent = annotCounts + '<br/><a target="_blank" href="http://www.wormbase.org/species/all/go_term/GO:' + nodeId + '#03--10">' + nodeName + '</a>';
          var qtipContent = annotCounts + '<br/><a target="_blank" href="http://amigo.geneontology.org/amigo/term/GO:' + nodeId + '">' + nodeName + '</a>';
          node.qtip({
               position: {
                 my: 'top center',
                 at: 'bottom center'
               },
               style: {
                 classes: 'qtip-bootstrap',
                 tip: {
                   width: 16,
                   height: 8
                 }
               },
               content: qtipContent,
               show: {
                  e: e.type,
                  ready: true
               },
               hide: {
                  e: 'mouseout unfocus'
               }
          }, e);
        });
        
        cyPhenGraph.on('tap', function(e){
          if( e.cyTarget === cyPhenGraph ){
            cyPhenGraph.elements().removeClass('faded');
          }
        });

        cyPhenGraph.on('mouseover', 'node', function(event) {
            var node = event.cyTarget;
            var nodeId   = node.data('id');
            var nodeName = node.data('name');
            var annotCounts = node.data('annotCounts');
//             var qtipContent = annotCounts + '<br/><a target="_blank" href="http://www.wormbase.org/species/all/go_term/GO:' + nodeId + '#03--10">' + nodeName + '</a>';
            var qtipContent = annotCounts + '<br/><a target="_blank" href="http://amigo.geneontology.org/amigo/term/GO:' + nodeId + '">' + nodeName + '</a>';
            \$('#info').html( qtipContent );
        });

// to fade out nodes on loading and remove buttons
        var nodes = cyPhenGraph.nodes();
//         var message = '';
//         cyPhenGraph.elements().addClass('faded');	// to fade all elements
        for( var i = 0; i < nodes.length; i++ ){
          var node     = nodes[i];
          var nodeId   = node.data('id');
          if (document.getElementById(nodeId)) { 	// if there's a button for this goslim term, remove faded
//             var neighborhood = node.neighborhood().add(node);
//             neighborhood.removeClass('faded');
//             node.removeClass('faded');		// to unfade goslim elements
            document.getElementById(nodeId).style.display = ''; }
//           message += nodeId + ' ';
        }
//         alert(message);

        var nodeCount = cyPhenGraph.nodes().length;
//         if (\$('#fakeRootFlag').is(':checked')) { nodeCount--; }	// Raymond will track that himself
        \$('#nodeCount').html('node count: ' + nodeCount + '<br/>');
        var edgeCount = cyPhenGraph.edges().length;
//         if (\$('#fakeRootFlag').is(':checked')) { edgeCount -= 3; }	// Raymond will track that himself
        \$('#edgeCount').html('edge count: ' + edgeCount + '<br/>');
      }

    });
  }


  \$('#radio_weighted').on('click', function(){
    var nodes = cyPhenGraph.nodes();
    for( var i = 0; i < nodes.length; i++ ){
      var node     = nodes[i];
      var nodeId   = node.data('id');
      var diameterWeighted   = node.data('diameter_weighted');
      cyPhenGraph.\$('#' + nodeId).data('diameter', diameterWeighted);
      var fontSizeWeighted   = node.data('fontSizeWeighted');
      cyPhenGraph.\$('#' + nodeId).data('fontSize', fontSizeWeighted);
    }
    cyPhenGraph.layout();
  });
  \$('#radio_unweighted').on('click', function(){
    var nodes = cyPhenGraph.nodes();
    for( var i = 0; i < nodes.length; i++ ){
      var node     = nodes[i];
      var nodeId   = node.data('id');
      var diameterUnweighted = node.data('diameter_unweighted');
      var diameterWeighted   = node.data('diameter_weighted');
      cyPhenGraph.\$('#' + nodeId).data('diameter', diameterUnweighted);
      var fontSizeUnweighted = node.data('fontSizeUnweighted');
      var fontSizeWeighted   = node.data('fontSizeWeighted');
      cyPhenGraph.\$('#' + nodeId).data('fontSize', fontSizeUnweighted);
    }
    cyPhenGraph.layout();
  });
  \$('#view_png_button').on('click', function(){
    var png64 = cyPhenGraph.png({full: true, maxWidth: 8000, maxHeight: 8000, bg: 'white'});
    \$('#png-export').attr('src', png64);
    \$('#png-export').show();
    \$('#exportdiv').show();
    \$('#cyPhenGraph').hide();
    \$('#weightstate').hide();
    \$('#view_png_button').hide();
    \$('#view_edit_button').show();
    \$('#info').text('drag image to desktop, or right-click and save image as');
  });
  \$('#view_edit_button').on('click', function(){
    \$('#png-export').hide();
    \$('#exportdiv').hide();
    \$('#cyPhenGraph').show();
    \$('#weightstate').show();
    \$('#view_png_button').show();
    \$('#view_edit_button').hide();
  });
  var updatingElements = ['radio_withiea', 'radio_excludeiea', 'radio_onlyiea', 'fakeRootFlag', 'filterForLcaFlag', 'filterLongestFlag', 'root_bp', 'root_cc', 'root_mf'];
//  var updatingElements = ['radio_withiea', 'radio_excludeiea', 'radio_onlyiea', 'fakeRootFlag', 'root_bp', 'root_cc', 'root_mf'];
  updatingElements.forEach(function(element) {
    \$('#'+element).on('click', updateElements); });
  function updateElements() {
    \$('#controldiv').hide(); \$('#loadingdiv').show();		// show loading and hide controls while graph loading
    var radioExcludeIea = \$('input[name=radio_iea]:checked').val();
    var rootsPossible = ['root_bp', 'root_cc', 'root_mf'];
    var rootsChosen = [];
    var fakeRootFlagValue = '0'; if (\$('#fakeRootFlag').is(':checked')) { fakeRootFlagValue = 1; }
    var filterForLcaFlagValue = '0'; if (\$('#filterForLcaFlag').is(':checked')) { filterForLcaFlagValue = 1; }
    var filterLongestFlagValue = '0'; if (\$('#filterLongestFlag').is(':checked')) { filterLongestFlagValue = 1; }
    rootsPossible.forEach(function(rootTerm) {
      if (document.getElementById(rootTerm).checked) { rootsChosen.push(document.getElementById(rootTerm).value); } });
    var rootsChosenGroup = rootsChosen.join(',');
    var url = 'soba_biggo.cgi?action=annotSummaryJson&focusTermId=$focusTermId&radio_iea=' + radioExcludeIea + '&rootsChosen=' + rootsChosenGroup + '&fakeRootFlag=' + fakeRootFlagValue + '&filterLongestFlag=' + filterLongestFlagValue + '&filterForLcaFlag=' + filterForLcaFlagValue;
//     alert(url); 
    var graphPNew = \$.ajax({
      url: url,
      type: 'GET',
      dataType: 'json'
    });
    Promise.all([ graphPNew ]).then(newCy);
    function newCy( then ){
//       cyPhenGraph.elements('node').hide();                     // hide all nodes
      var elementsNew = then[0].elements;
      cyPhenGraph.json( { elements: elementsNew } );
      cyPhenGraph.elements().layout({ name: 'dagre', padding: 10, nodeSep: 5 });
      \$('#controldiv').show(); \$('#loadingdiv').hide();	// show controls and hide loading when graph loaded
      var nodeCount = cyPhenGraph.nodes().length;
      if (\$('#fakeRootFlag').is(':checked')) { nodeCount--; }
      \$('#nodeCount').html('node count: ' + nodeCount + '<br/>');
      var edgeCount = cyPhenGraph.edges().length;
      \$('#edgeCount').html('edge count: ' + edgeCount + '<br/>');


//       var nodeHash = new Object();                                    // put nodes here that have an edge that shows
//       var arrayEdges = cyPhenGraph.elements('edge');       // get the edges in an array
//       for (k = 0; k < arrayEdges.length; k++) {                   // for each edge
//           nodeHash[arrayEdges[k].data().source]++                 // add the source node to hash of nodes to show
//           nodeHash[arrayEdges[k].data().target]++                 // add the target node to hash of nodes to show
//       }
// var toAlert = '';
//       var arrayNodes = cyPhenGraph.elements('node');       // get the edges in an array
//       for (k = 0; k < arrayNodes.length; k++) {                   // for each edge
//         var thisNode = arrayNodes[k].data().id; 
// toAlert += ' ' + thisNode;
//       }
// alert(toAlert);

//       cyPhenGraph.elements('node').hide();                     // hide all nodes
//       cyPhenGraph.elements('node').filter(function(i, ele){    // filter on nodes
//         if (nodeHash.hasOwnProperty(ele.id())) {                      // if the node is is in the hash of nodes to show
//           ele.show();                                                 // show the node
//         }
//       });
//       cyPhenGraph.elements().layout({ name: 'dagre', padding: 10, nodeSep: 5 });
    }
  }


});
</script>

</head>
<body>
<div style="width: 1705px;">
  <div id="cyPhenGraph"  style="border: 1px solid #aaa; float: left;  position: relative; height: 1050px; width: 1050px;"></div>
  <div id="exportdiv" style="width: 1050px; height: 1050px; position: relative; float: left; display: none;"><img id="png-export" style="border: 1px solid #ddd; display: none; max-width: 1050px; max-height: 1050px"></div>
    <div id="loading">
      <span class="fa fa-refresh fa-spin"></span>
    </div>
  <!--<div id="cy2" style="border: 1px solid #aaa; float: left; position: relative; height: 1050px; width: 400px;"></div>-->
  <!--<div id="cy" style="height: 100%; width: 100%; position: absolute;"></div>-->
  <div id="loadingdiv" style="z-index: 9999; border: 1px solid #aaa; position: relative; float: left; width: 200px; display: '';">Loading <img src="loading.gif" /></div>
  <div id="controldiv" style="z-index: 9999; border: 1px solid #aaa; position: relative; float: left; width: 200px; display: none;">
    <div id="exportdiv" style="z-index: 9999; position: relative; top: 0; left: 0; width: 200px;">
      <button id="view_png_button">export png</button>
      <button id="view_edit_button" style="display: none;">go back</button><br/>
    </div>
    <div id="legenddiv" style="z-index: 9999; position: relative; top: 0; left: 0; width: 200px;">
    <span id="autocompleteValue">$autocompleteValue</span><br/><br/>
    <span id="nodeCount" style="display: $show_node_count ">node count<br/></span>
    <span id="edgeCount" style="display: $show_node_count ">edge count<br/></span>
    Legend :<br/>
    <table>
    <tr><td valign="center"><svg width="22pt" height="22pt" viewBox="0.00 0.00 44.00 44.00" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
    <g id="graph0" class="graph" transform="scale(1 1) rotate(0) translate(4 40)">
    <polygon fill="white" stroke="none" points="-4,4 -4,-40 40,-40 40,4 -4,4"/>
    <g id="node1" class="node"><title></title>
    <polygon fill="none" stroke="blue" stroke-dasharray="5,2" points="36,-36 0,-36 0,-0 36,-0 36,-36"/></g></g></svg></td><td valign="center">Root</td></tr>
    <tr><td valign="center"><svg width="22pt" height="22pt" viewBox="0.00 0.00 44.00 44.00" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
    <g id="graph0" class="graph" transform="scale(1 1) rotate(0) translate(4 40)">
    <polygon fill="white" stroke="none" points="-4,4 -4,-40 40,-40 40,4 -4,4"/>
    <g id="node1" class="node"><title></title>
    <ellipse fill="none" stroke="blue" stroke-dasharray="5,2" cx="18" cy="-18" rx="18" ry="18"/></g></g></svg></td><td valign="center">Without Direct Annotation</td></tr>
    <tr><td valign="center"><svg width="22pt" height="22pt" viewBox="0.00 0.00 44.00 44.00" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
    <g id="graph0" class="graph" transform="scale(1 1) rotate(0) translate(4 40)">
    <polygon fill="white" stroke="none" points="-4,4 -4,-40 40,-40 40,4 -4,4"/>
    <g id="node1" class="node"><title></title>
    <ellipse fill="none" stroke="red" cx="18" cy="-18" rx="18" ry="18"/></g></g></svg></td><td valign="center">With Direct Annotation</td></tr>
    <tr><td valign="center"><svg width="22pt" height="22pt" viewBox="0.00 0.00 44.00 44.00"> <g class="graph" transform="scale(1 1) rotate(0) translate(4 40)"> <polygon points="-4,4 -4,-40 40,-40 40,4 -4,4" fill="white" /> <g class="node" style="fill:#ff0000;fill-opacity:1" transform="translate(0,-19.2)"> <path d="M 35.99863,-0.58027907 A 18,18 0 0 1 27.088325,15.178899 18,18 0 0 1 8.9846389,15.221349 18,18 0 0 1 5.2625201e-4,-0.49586946" transform="scale(1,-1)" /> </g> <path style="fill:#0000ff;fill-opacity:1;stroke:#0000ff;stroke-width:1;stroke-dasharray:5, 2" d="m 36.07799,-18.703936 a 18,18 0 0 1 -9.000001,15.5884578 18,18 0 0 1 -17.9999999,-4e-7 18,18 0 0 1 -8.99999952,-15.5884574" /> </g> </svg></td><td valign="center">AGR Slim terms</td></tr>
    </table></div>
    <form method="get" action="soba_biggo.cgi">
      <div id="weightstate" style="z-index: 9999; position: relative; top: 0; left: 0; width: 200px;">
        <input type="radio" name="radio_type" id="radio_weighted"   checked="checked" >Annotation weighted</input><br/>
        <input type="radio" name="radio_type" id="radio_unweighted">Annotation unweighted</input><br/>
      </div><br/>
      <div id="ieastate" style="z-index: 9999; position: relative; top: 0; left: 0; width: 200px;">
        <input type="radio" name="radio_iea" id="radio_withiea"    value="radio_withiea"    $checked_radio_withiea >all evidence types</input><br/>
        <input type="radio" name="radio_iea" id="radio_excludeiea" value="radio_excludeiea" $checked_radio_excludeiea >exclude IEA</input><br/>
        <input type="radio" name="radio_iea" id="radio_onlyiea" value="radio_onlyiea" $checked_radio_onlyiea >experimental evidence only</input><br/>
      </div><br/>
      <div id="rootschosen" style="z-index: 9999; position: relative; top: 0; left: 0; width: 200px;">
        <input type="checkbox" name="root_bp" id="root_bp" value="GO:0008150" $checked_root_bp >Biological Process</input><br/>
        <input type="checkbox" name="root_cc" id="root_cc" value="GO:0005575" $checked_root_cc >Cellular Component</input><br/>
        <input type="checkbox" name="root_mf" id="root_mf" value="GO:0003674" $checked_root_mf >Molecular Function</input><br/>
      </div><br/>
      <!--<input type="submit" name="action" value="update graph"><br/>-->
      <input type="hidden" name="focusTermId" value="$focusTermId">
      <div id="controlMenu" style="display: $displayControlMenu;">
        <input type="checkbox" id="showControlsFlag"  name="showControlsFlag"  value="1" $checked_showControls>Show Controls<br/>
        <div id="hidethis" style="display: none;"> <input type="checkbox" id="nodeCountFlag"     name="nodeCountFlag"     value="1" $checked_nodeCount>Node Count<br/></div>
        <input type="checkbox" id="fakeRootFlag"      name="fakeRootFlag"      value="1" $checked_fakeRoot>Fake Root<br/>
        <input type="checkbox" id="filterForLcaFlag"  name="filterForLcaFlag"  value="1" $checked_filterLca>Filter LCA Nodes<br/>
        <input type="checkbox" id="filterLongestFlag" name="filterLongestFlag" value="1" $checked_filterLongest>Filter Longest Edges<br/>
      </div>
<!-- additional options, code still in place to support them
-->
    </form>
    <div id="info" style="z-index: 9999; position: relative; top: 0; left: 0; width: 200px;">Mouseover or click node for more information.</div><br/>
    $goslimButtons<br/>
  </div>
</div>
EndOfText
print qq($return);
print qq($toPrint);
print qq(</body></html>);
} # sub annotSummaryCytoscape

# horizontal
# <svg width="288pt" height="94pt"
#  viewBox="0.00 0.00 288.13 94.27" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
# <g id="graph0" class="graph" transform="scale(1 1) rotate(0) translate(4 90.267)">
# <title>test0</title>
# <polygon fill="white" stroke="none" points="-4,4 -4,-90.267 284.134,-90.267 284.134,4 -4,4"/>
# <!-- With\nDirect\nAnnotation -->
# <g id="node1" class="node"><title>With\nDirect\nAnnotation</title>
# <ellipse fill="none" stroke="red" cx="43.1335" cy="-43.1335" rx="43.2674" ry="43.2674"/>
# <text text-anchor="middle" x="43.1335" y="-54.4335" font-family="Times,serif" font-size="14.00">With</text>
# <text text-anchor="middle" x="43.1335" y="-39.4335" font-family="Times,serif" font-size="14.00">Direct</text>
# <text text-anchor="middle" x="43.1335" y="-24.4335" font-family="Times,serif" font-size="14.00">Annotation</text>
# </g>
# <!-- Without\nDirect\nAnnotation -->
# <g id="node2" class="node"><title>Without\nDirect\nAnnotation</title>
# <ellipse fill="none" stroke="blue" stroke-dasharray="5,2" cx="147.134" cy="-43.1335" rx="43.2674" ry="43.2674"/>
# <text text-anchor="middle" x="147.134" y="-54.4335" font-family="Times,serif" font-size="14.00">Without</text>
# <text text-anchor="middle" x="147.134" y="-39.4335" font-family="Times,serif" font-size="14.00">Direct</text>
# <text text-anchor="middle" x="147.134" y="-24.4335" font-family="Times,serif" font-size="14.00">Annotation</text>
# </g>
# <!-- Root -->
# <g id="node3" class="node"><title>Root</title>
# <polygon fill="none" stroke="blue" stroke-dasharray="5,2" points="280.134,-79.1335 208.134,-79.1335 208.134,-7.13351 280.134,-7.13351 280.134,-79.1335"/>
# <text text-anchor="middle" x="244.134" y="-39.4335" font-family="Times,serif" font-size="14.00">Root</text>
# </g>
# </g>
# </svg>

sub svgCleanup {
  my ($svgGenerated, $focusTermId) = @_;
  my ($svgMarkup) = $svgGenerated =~ m/(<svg.*<\/svg>)/s;             # capture svg markup
# print STDERR qq($svgMarkup\n);
  my ($height, $width) = ('', '');
  if ($svgMarkup =~ m/<svg width="(\d+)pt" height="(\d+)pt"/) { $width = $1; $height = $2; }
  my $hwratio = $height / $width;
  my $widthResolution = 960;
  if ($width > $widthResolution) { 
    my $newwidth  = $widthResolution;
    my $newheight = int($newwidth * $hwratio);
    $svgMarkup =~ s/<svg width="${width}pt" height="${height}pt"/<svg width="${newwidth}pt" height="${newheight}pt"/g;
  }
#   $svgMarkup =~ s/<title>legend_legend--legend_root<\/title>//g;                            # remove automatic title
#   $svgMarkup =~ s/<title>legend_legend<\/title>//g;                            # remove automatic title
#   $svgMarkup =~ s/<title>legend_root<\/title>//g;                            # remove automatic title
#   $svgMarkup =~ s/<title>legend_nodirect<\/title>//g;                            # remove automatic title
  $svgMarkup =~ s/<title>[^<]*?<\/title>/<title>${focusTermId}Phenotypes<\/title>/g;                            # remove automatic title
  $svgMarkup =~ s/<title>test<\/title>//g;                            # remove automatic title
  $svgMarkup =~ s/<title>Perl<\/title>//g;                            # remove automatic title
  $svgMarkup =~ s/_placeholderColon_/:/g;                             # ids can't be created with a : in them, so have to add the : after the svg is generated
  $svgMarkup =~ s/LINEBREAK//g;                             		# remove leading hidden linebreak to offset counts of rnai and variation in transparent line afterward
  $svgMarkup =~ s/fill="#fffffe"/fill="rgba\(0,0,0,0.01\)"/g;		# cannot set opacity value directly at creating, so setting fontcolor to transparent, which becomes #fffffe which we can replace with an rgba with very low opacity
  my (@xlinkTitle) = $svgMarkup =~ m/xlink:title="(.*?)"/g;
  foreach my $xlt (@xlinkTitle) {
# print STDERR qq($xlt\n);
    my $xltEdited = $xlt;
    $xltEdited =~ s/&lt;br\/&gt;/\n/g;
    $xltEdited =~ s/&lt;\/?b&gt;//g;
    $xltEdited =~ s/&lt;font color=&quot;transparent&quot;&gt;//g;
    $xltEdited =~ s/&lt;\/font&gt;//g;
#     $xltEdited =~ s/&lt;[^&]*?&gt;//g;
#     $xltEdited =~ s/<.*?>//g;
    $xltEdited =~ s/^\n//;						# remove leading linebreak added by placeholder line break for centering label
    $svgMarkup =~ s/$xlt/$xltEdited/g; 
# print "XLT $xlt -> XLTE $xltEdited<br/>";
  } # foreach my $xlt (@xlinkTitle)
  return $svgMarkup;
} # sub svgCleanup

sub calculateLCA {						# find all lowest common ancestors
  my ($ph1, $ph2) = @_;
  my @terms = ( $ph1, $ph2 );
  my %amountInBoth;
  my %inBoth;							# get all nodes that are in both sets
  foreach my $annotTerm (@terms) {
    foreach my $phenotype (sort keys %{ $nodesAll{$annotTerm} }) {
      $amountInBoth{$phenotype}++; } }
  foreach my $term (sort keys %amountInBoth) { if ($amountInBoth{$term} > 1) { $inBoth{$term}++; } }
  %ancestorNodes = ();
#   foreach my $inBoth (sort keys %inBoth) { print qq($ph1, $ph2 INB $inBoth<br>); }
  foreach my $annotTerm (@terms) {
    foreach my $child (sort keys %{ $edgesAll{$annotTerm} }) {
      if ($inBoth{$child}) {
        foreach my $parent (sort keys %{ $edgesAll{$annotTerm}{$child} }) { $ancestorNodes{$parent}++; } } } }
  my %lca;
  foreach my $bothNode (sort keys %inBoth) {
    unless ($ancestorNodes{$bothNode}) { $lca{$bothNode}++; }
#     print qq($ph1 $ph2 BOTH $bothNode -- );
#     if ($ancestorNodes{$bothNode}) { print qq(ANCESTOR $bothNode --); }
#     print qq(<br/>);
  }
  return \%lca;
} # sub calculateLCA

# sub addToAncestors {
#   my ($annotTerm, $bothNode) = @_;
#   foreach my $parent (sort keys %{ $edgesAll{$annotTerm}{$bothNode} }) {
# print qq(AT $annotTerm CHILD $bothNode PARENT $parent<br>);
#     $ancestorNodes{$parent}++;
#     &addToAncestors($annotTerm, $parent);
#   }
# } # sub addToAncestors


# sub getGenesCountHash {				# for a given focusTermId, get the genes count of itself and its direct children, option direct or inferred genes
#   my ($focusTermId, $directOrInferred) = @_;
#   my %genesCount;				# count of genes for the given direct vs inferred
#   my ($solr_url) = &getSolrUrl($focusTermId);
#   my $url = $solr_url . 'select?qt=standard&indent=on&wt=json&version=2.2&fl=id&start=0&rows=10000000&q=document_category:bioentity&facet=true&facet.field=annotation_class_list&facet.limit=-1&facet.mincount=1&facet.sort=count&fq=source:%22WB%22&fq=annotation_class_list:%22' . $focusTermId . '%22';
# # print "URL $url URL";		# currently not getting the right counts because facet_count->facet_fields->annotation_class_list is empty.  2013 11 09
#   my $searchField = 'annotation_class_list';	# by default assume direct search for URL and JSON field
#   if ($directOrInferred eq 'inferred') { 	# if inferred, change the URL and JSON field
#     $searchField = 'regulates_closure';
# # Raymond might want to try this  2017 01 09
# # http://wobr2.caltech.edu:8080/solr/go/select?qt=standard&indent=on&wt=json&version=2.2&rows=1000000&fl=regulates_closure,id,annotation_class&q=document_category:annotation&fq=-qualifier:%22not%22&fq=bioentity:%22WB:WBGene00000899%22
#     $url = $solr_url . 'select?qt=standard&indent=on&wt=json&version=2.2&fl=id&start=0&rows=10000000&q=document_category:bioentity&facet=true&facet.field=regulates_closure&facet.limit=-1&facet.mincount=1&facet.sort=count&fq=source:%22WB%22&fq=regulates_closure:%22' . $focusTermId . '%22'; }
# print qq(URL $url URL\n);
#   my $page_data = get $url;
#   my $perl_scalar = $json->decode( $page_data );
#   my %jsonHash = %$perl_scalar;
# 
#   $genesCount{$focusTermId} = $jsonHash{'response'}{'numFound'}; 	# get the main focusTermId gene count and store in %genesCount
#   while (scalar @{ $jsonHash{'facet_counts'}{'facet_fields'}{$searchField} } > 0) {	# while there are pairs of genes/count in the JSON array
#     my $focusTermId = shift @{ $jsonHash{'facet_counts'}{'facet_fields'}{$searchField} }; # get the focusTermId
#     my $count = shift @{ $jsonHash{'facet_counts'}{'facet_fields'}{$searchField} }; 	# get the count
#     $genesCount{$focusTermId} = $count;							# add the mapping to %genesCount
#   } # while (scalar @{ $jsonHash{'facet_counts'}{'facet_fields'}{$searchField} } > 0)
# 
#   return \%genesCount;
# } # sub getGenesCountHash

# sub getLongestPathAndTransitivity {			# given two nodes, get the longest path and dominant inferred transitivity
#   my ($ancestor, $focusTermId) = @_;					# the ancestor and focusTermId from which to find the longest path
#   &recurseLongestPath($focusTermId, $focusTermId, $ancestor, $focusTermId);	# recurse to find longest path given current, start, end, and list of current path
#   my $max_nodes = 0;							# the most nodes found among all paths travelled
#   my %each_finalpath_transitivity;					# hash of inferred sensitivity value for each path that finished
#   foreach my $finpath (@{ $paths{"finalpath"} }) {			# for each of the paths that reached the end node
#     my $nodes = scalar @$finpath;					# amount of nodes in the path
#     if ($nodes > $max_nodes) { $max_nodes = $nodes; }			# if more nodes than max, set new max
# 
#     my $child = shift @$finpath; my $parent = shift @$finpath;		# get first node and its parent along this path
#     my $relationship_one = $paths{"childToParent"}{$child}{$parent};	# get relationship between them (from json)
#     my $relationship_two = '';						# initialize relationship between parent and its parent 
#     while (scalar @$finpath > 0) {					# while there are steps in the path
#       $child = $parent;							# the child in the new step is the previous parent
#       $parent = shift @$finpath;					# the new parent is the next node in the path
#       $relationship_two = $paths{"childToParent"}{$child}{$parent};	# the second relationship is the relationship between this pair
#       $relationship_one = &getInferredRelationship($relationship_one, $relationship_two); 	# get inferred relationship given those two relationships
#     }
#     $each_finalpath_transitivity{$relationship_one}++;			# add final inferred transitivity relationship to hash
#   } # foreach my $finpath (@finalpath)
#   delete $paths{"finalpath"};						# reset finalpath for other ancestors
#   my $max_steps = $max_nodes - 1;					# amount of steps is one less than amount of nodes
# 
#   my %transitivity_priority;						# when different paths have different inferred transitivity, highest number takes precedence
#   $transitivity_priority{"is_a"}                 = 1;
#   $transitivity_priority{"has_part"}             = 2;
#   $transitivity_priority{"part_of"}              = 3;
#   $transitivity_priority{"regulates"}            = 4;
#   $transitivity_priority{"negatively_regulates"} = 5;
#   $transitivity_priority{"positively_regulates"} = 6;
#   $transitivity_priority{"occurs_in"}            = 7;
#   $transitivity_priority{"unknown"}              = 8;			# in case some relationship or pair of relationships is unaccounted for
#   my @all_inferred_paths_transitivity = sort { $transitivity_priority{$b} <=> $transitivity_priority{$a} } keys %each_finalpath_transitivity ;
# 									# sort all inferred transitivities by highest precedence
#   my $dominant_inferred_transitivity = shift @all_inferred_paths_transitivity;	# dominant is the one with highest precedence
#   return ($max_steps, $dominant_inferred_transitivity);			# return the maximum number of steps and dominant inferred transitivity
# # my ($relationship) = &getInferredRelationship($one, $two); 
# } # sub getLongestPathAndTransitivity 
# 
# sub recurseLongestPath {
#   my ($current, $start, $end, $curpath) = @_;				# current node, starting node, end node, path travelled so far
#   my %ignoreNonTransitivePredicate;					# there predicate relationships from the topoHash are non transitive and should be ignored for determining indendation depth (pretend the edge doesn't exist) 2013 11 13
#   $ignoreNonTransitivePredicate{"daughter_of"}++;
#   $ignoreNonTransitivePredicate{"daughter_of_in_hermaphrodite"}++;
#   $ignoreNonTransitivePredicate{"daughter_of_in_male"}++;
#   $ignoreNonTransitivePredicate{"develops_from"}++;
#   $ignoreNonTransitivePredicate{"exclusive_union_of"}++;
#   foreach my $parent (sort keys %{ $paths{"childToParent"}{$current} }) {	# for each parent of the current node
#     next if ($ignoreNonTransitivePredicate{$paths{"childToParent"}{$current}{$parent}});	# skip non-transitive edges
#     my @curpath = split/\t/, $curpath;					# convert current path to array
#     push @curpath, $parent;						# add the current parent
#     if ($parent eq $end) {						# if current parent is the end node
#         my @tmpWay = @curpath;						# make a copy of the array
#         push @{ $paths{"finalpath"} }, \@tmpWay; }			# put a reference to the array copy into the finalpath
#       else {								# not the end node yet
#         my $curpath = join"\t", @curpath;				# pass literal current path instead of reference
#         &recurseLongestPath($parent, $start, $end, $curpath); }		# recurse to keep looking for the final node
#   } # foreach $parent (sort keys %{ $paths{"childToParent"}{$current} })
# } # sub recurseLongestPath

sub getLongestPathAndTransitivity {			# given two nodes, get the longest path and dominant inferred transitivity
  my ($ancestor, $focusTermId) = @_;					# the ancestor and focusTermId from which to find the longest path
  &recurseLongestPath($focusTermId, $focusTermId, $ancestor, $focusTermId);	# recurse to find longest path given current, start, end, and list of current path
  my $max_nodes = 0;							# the most nodes found among all paths travelled
  my %each_finalpath_transitivity;					# hash of inferred sensitivity value for each path that finished
  my %edgesByNodeCount;
  foreach my $finpath (@{ $paths{"finalpath"} }) {			# for each of the paths that reached the end node
    my $nodeCount = scalar @$finpath;					# amount of nodes in the path
    if ($nodeCount > $max_nodes) { $max_nodes = $nodeCount; }		# if more nodes than max, set new max
    push @{ $edgesByNodeCount{$nodeCount} }, $finpath;
  } # foreach my $finpath (@finalpath)
  my %edgesFromFinalPath;							# edges calculate from final paths. key 'longest' if from longest path, or 'notlongest' if exist in a non-longest path.  subkey source, subsubkey target.
  foreach my $nodeCount (sort keys %edgesByNodeCount) {
    foreach my $finpath (@{ $edgesByNodeCount{$nodeCount} }) {
# print qq(FIN $finpath A @$finpath PATH\n);
      my $nodes     = join", ", @$finpath;
      my @finalpath = @$finpath;					# array of nodes connecting a final path
      my $fromLongestPath = 'longest';
      if ($nodeCount eq $max_nodes) { $fromLongestPath = 'longest'; }
         else { $fromLongestPath = 'notlongest'; }
      for my $i (0 .. $nodeCount - 2) {					# get pairs of edges
        my $source = $finalpath[$i]; 
        my $target = $finalpath[$i+1]; 
        $edgesFromFinalPath{$fromLongestPath}{$source}{$target}++;	# sort into hash of edges derived from final paths
#         print qq(FLP $fromLongestPath S $source T $target E\n);
      }
#       print qq(FIN $nodeCount PATH $nodes\n);
    } # foreach my $finpath (sort keys %{ $edgesByNodeCount{$nodeCount} })
  } # foreach my $nodeCount (sort keys %edgesByNodeCount)
  return \%edgesFromFinalPath;
} # sub getLongestPathAndTransitivity 

sub recurseLongestPath {
  my ($current, $start, $end, $curpath) = @_;				# current node, starting node, end node, path travelled so far
  foreach my $parent (sort keys %{ $paths{"childToParent"}{$current} }) {	# for each parent of the current node
    my @curpath = split/\t/, $curpath;					# convert current path to array
    push @curpath, $parent;						# add the current parent
    if ($parent eq $end) {						# if current parent is the end node
        my @tmpWay = @curpath;						# make a copy of the array
        push @{ $paths{"finalpath"} }, \@tmpWay; }			# put a reference to the array copy into the finalpath
      else {								# not the end node yet
        my $curpath = join"\t", @curpath;				# pass literal current path instead of reference
        &recurseLongestPath($parent, $start, $end, $curpath); }		# recurse to keep looking for the final node
  } # foreach $parent (sort keys %{ $paths{"childToParent"}{$current} })
} # sub recurseLongestPath

sub getInferredRelationship {
  my ($one, $two) = @_; my $relationship = 'unknown';
  if ($one eq 'is_a') {
      if ($two eq 'is_a') {                     $relationship = 'is_a';                  }
      elsif ($two eq 'part_of') {               $relationship = 'part_of';               }
      elsif ($two eq 'regulates') {             $relationship = 'regulates';             }
      elsif ($two eq 'positively_regulates') {  $relationship = 'positively_regulates';  }
      elsif ($two eq 'negatively_regulates') {  $relationship = 'negatively_regulates';  }
      elsif ($two eq 'has_part') {              $relationship = 'has_part';              } }
    elsif ($one eq 'part_of') { 
      if ($two eq 'is_a') {                     $relationship = 'part_of';               }
      elsif ($two eq 'part_of') {               $relationship = 'part_of';               } }
    elsif ($one eq 'regulates') { 
      if ($two eq 'is_a') {                     $relationship = 'regulates';             }
      elsif ($two eq 'part_of') {               $relationship = 'regulates';             } }
    elsif ($one eq 'positively_regulates') { 
      if ($two eq 'is_a') {                     $relationship = 'positively_regulates';  }
      elsif ($two eq 'part_of') {               $relationship = 'regulates';             } }
    elsif ($one eq 'negatively_regulates') { 
      if ($two eq 'is_a') {                     $relationship = 'negatively_regulates';  }
      elsif ($two eq 'part_of') {               $relationship = 'regulates';             } }
    elsif ($one eq 'has_part') { 
      if ($two eq 'is_a') {                     $relationship = 'has_part';              }
      elsif ($two eq 'has_part') {              $relationship = 'has_part';              } }
  return $relationship;
} # sub getInferredRelationship

sub makeLink {
  my ($focusTermId, $text) = @_;
  my $url = "soba_biggo.cgi?action=Tree&focusTermId=$focusTermId";
  my $link = qq(<a href="$url">$text</a>);
  return $link;
} # sub makeLink

sub printHtmlFooter { print qq(</body></html>\n); }

sub printHtmlHeader { 
  my $javascript = << "EndOfText";
<script src="http://code.jquery.com/jquery-1.9.1.js"></script>
<!--<script src="amigo.js"></script>-->
<script type="text/javascript">
function toggleShowHide(element) {
    document.getElementById(element).style.display = (document.getElementById(element).style.display == "none") ? "" : "none";
    return false;
}
function togglePlusMinus(element) {
    document.getElementById(element).innerHTML = (document.getElementById(element).innerHTML == "&nbsp;+&nbsp;") ? "&nbsp;-&nbsp;" : "&nbsp;+&nbsp;";
    return false;
}
</script>
EndOfText
  print qq(Content-type: text/html\n\n<html><head><title>Amigo testing</title>$javascript</head><body>\n); }

sub getHtmlVar {                
  no strict 'refs';             
  my ($query, $var, $err) = @_; 
  unless ($query->param("$var")) {
    if ($err) { print "<FONT COLOR=blue>ERROR : No such variable : $var</FONT><BR>\n"; }
  } else { 
    my $oop = $query->param("$var");
    $$var = &untaint($oop);         
    return ($var, $$var);           
  } 
} # sub getHtmlVar

sub untaint {
  my $tainted = shift;
  my $untainted;
  if ($tainted eq "") {
    $untainted = "";
  } else { # if ($tainted eq "")
    $tainted =~ s/[^\w\-.,;:?\/\\@#\$\%\^&*\>\<(){}[\]+=!~|' \t\n\r\f\"€‚ƒ„…†‡ˆ‰Š‹ŒŽ‘’“”•—˜™š›œžŸ¡¢£¤¥¦§¨©ª«¬­®¯°±²³´µ¶·¹º»¼½¾¿ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþ]//g;
    if ($tainted =~ m/^([\w\-.,;:?\/\\@#\$\%&\^*\>\<(){}[\]+=!~|' \t\n\r\f\"€‚ƒ„…†‡ˆ‰Š‹ŒŽ‘’“”•—˜™š›œžŸ¡¢£¤¥¦§¨©ª«¬­®¯°±²³´µ¶·¹º»¼½¾¿ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþ]+)$/) {
      $untainted = $1;
    } else {
      die "Bad data Tainted in $tainted";
    }
  } # else # if ($tainted eq "")
  return $untainted;
} # sub untaint


