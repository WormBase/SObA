#!/usr/bin/perl 

# partially cleaned up amigo.cgi from 12.204 to only produce SObA  2016 12 14

# /~raymond/cgi-bin/soba_biggo.cgi?action=annotSummaryCytoscape&autocompleteValue=F56F4.3%20(Caenorhabditis%20elegans,%20WB:WBGene00018980,%20-,%20-)&showControlsFlag=1

# on wormbase
#  root/templates/classes/gene/phenotype_graph.tt2
#  lib/WormBase/API/Object/Gene.pm
#  root/js/wormbase.js

# anatomy, disease, go, lifestage, and phenotype

# Show "No observed ...", e.g.
# https://wormbase.org/species/c_elegans/gene/WBGene00002159#0b--10

# ZK512.8



use CGI;
use strict;
use LWP::Simple;
use LWP::UserAgent;
use JSON;
use Tie::IxHash;                                # allow hashes ordered by item added
use Net::Domain qw(hostname hostfqdn hostdomain);



use Storable qw(dclone);			# copy hash of hashes

use Time::HiRes qw( time );
my $startTime = time; my $prevTime = time;
$startTime =~ s/(\....).*$/$1/;
$prevTime  =~ s/(\....).*$/$1/;

my $hostname = hostname();


# my $top_datatype = 'phenotype';
my $json = JSON->new->allow_nonref;
my $query = new CGI;
# my $base_solr_url = "http://localhost:8080/solr/$top_datatype/";		# big geneontology golr server
my $base_solr_url = "http://localhost:8080/solr/";		# big geneontology golr server


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

  if ($action eq 'annotSummaryCytoscape')      { &annotSummaryCytoscape('all_roots'); }
    elsif ($action eq 'annotSummaryGraph')          { &annotSummaryGraph();     }
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
  my ($var, $datatype) = &getHtmlVar($query, 'datatype');
  my $max_results = 20; 
  my $escapedWords = $words;
  my $lcwords = lc($escapedWords);
  my $ucwords = uc($escapedWords);
  $escapedWords =~ s/ /%5C%20/g;
  $escapedWords =~ s/:/\\:/g;
  my %matches; my $t = tie %matches, "Tie::IxHash";     # sorted hash to filter results

  my $datatype_solr_url = $base_solr_url . $datatype . '/';

# Exact match (case sensitive)
  my $solr_gene_url = $datatype_solr_url . 'select?qt=standard&fl=score,id,bioentity_internal_id,synonym,bioentity_label,bioentity_name,taxon,taxon_label&version=2.2&wt=json&rows=' . $max_results . '&indent=on&q=*:*&fq=document_category:%22bioentity%22&fq=(bioentity_internal_id:' . $escapedWords . '+OR+bioentity_label:' . $escapedWords . '+OR+bioentity_name:' . $escapedWords . '+OR+synonym:' . $escapedWords . ')';
  if ($taxonFq) { $solr_gene_url .= "&fq=($taxonFq)"; }
  my ($matchesHashref) = &solrSearch( $solr_gene_url, \%matches, $max_results);
  %matches = %$matchesHashref;

# String wildcard match (case sensitive)
  my $matchesCount = scalar keys %matches;
  if ($matchesCount < $max_results) {
    my $extraMatchesCount = $max_results - $matchesCount;
   $solr_gene_url = $datatype_solr_url . 'select?qt=standard&fl=score,id,bioentity_internal_id,synonym,bioentity_label,bioentity_name,taxon,taxon_label&version=2.2&wt=json&rows=' . $max_results . '&indent=on&q=*:*&fq=document_category:%22bioentity%22&fq=(bioentity_internal_id:' . $escapedWords . '*+OR+bioentity_label:' . $escapedWords . '*+OR+bioentity_name:' . $escapedWords . '*+OR+synonym:' . $escapedWords . '*)';
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
      $solr_gene_url = $datatype_solr_url . 'select?qt=standard&fl=score,id,bioentity_internal_id,synonym,bioentity_label,bioentity_name,taxon,taxon_label&version=2.2&wt=json&rows=' . $max_results . '&indent=on&q=*:*&fq=document_category:%22bioentity%22&fq=((bioentity_internal_id_searchable:"' . $firstWord . '"+AND+bioentity_internal_id_searchable:' . $lastWord . '*)+OR+(bioentity_name_searchable:"' . $firstWord . '"+AND+bioentity_name_searchable:' . $lastWord . '*)+OR+(bioentity_label_searchable:"' . $firstWord . '"+AND+bioentity_label_searchable:' . $lastWord . '*)+OR+(synonym_searchable:"' . $firstWord . '"+AND+synonym_searchable:' . $lastWord . '*))';

# :8080/solr/$datatype/select?qt=standard&fl=score,id,bioentity_internal_id,bioentity_label,bioentity_name,synonym,taxon,taxon_label&version=2.2&wt=json&rows=500&indent=on&q=*:*&fq=document_category:%22bioentity%22&fq=


      if ($taxonFq) { $solr_gene_url .= "&fq=($taxonFq)"; }
      my ($matchesHashref) = &solrSearch( $solr_gene_url, \%matches, $max_results);
      %matches = %$matchesHashref;
    } else {		# not a phrase

    # Exact match (case insensitive _searchable)
      $matchesCount = scalar keys %matches;
      if ($matchesCount < $max_results) {
        my $extraMatchesCount = $max_results - $matchesCount;
        $solr_gene_url = $datatype_solr_url . 'select?qt=standard&fl=score,id,bioentity_internal_id,synonym,bioentity_label,bioentity_name,taxon,taxon_label&version=2.2&wt=json&rows=' . $max_results . '&indent=on&q=*:*&fq=document_category:%22bioentity%22&fq=(bioentity_internal_id_searchable:' . $escapedWords . '+OR+bioentity_label_searchable:' . $escapedWords . '+OR+bioentity_name_searchable:' . $escapedWords . '+OR+synonym_searchable:' . $escapedWords . ')';
        if ($taxonFq) { $solr_gene_url .= "&fq=($taxonFq)"; }
        my ($matchesHashref) = &solrSearch( $solr_gene_url, \%matches, $max_results);
        %matches = %$matchesHashref;
      }

    # Starting with word Wildcard match (case insensitive _searchable)
      $matchesCount = scalar keys %matches;
      if ($matchesCount < $max_results) {
        my $extraMatchesCount = $max_results - $matchesCount;
        $solr_gene_url = $datatype_solr_url . 'select?qt=standard&fl=score,id,bioentity_internal_id,synonym,bioentity_label,bioentity_name,taxon,taxon_label&version=2.2&wt=json&rows=' . $max_results . '&indent=on&q=*:*&fq=document_category:%22bioentity%22&fq=(bioentity_internal_id_searchable:' . $escapedWords . '*+OR+bioentity_label_searchable:' . $escapedWords . '*+OR+bioentity_name_searchable:' . $escapedWords . '*+OR+synonym_searchable:' . $escapedWords . '*)';
        if ($taxonFq) { $solr_gene_url .= "&fq=($taxonFq)"; }
        my ($matchesHashref) = &solrSearch( $solr_gene_url, \%matches, $max_results);
        %matches = %$matchesHashref;
      }
  }

  my $matches = join"\n", keys %matches;
  print $matches;
} # sub autocompleteGene


sub solrSearch {
  my ($solr_gene_url, $matchesHashref, $max_results) = @_;

  my $matchesCount = scalar keys %$matchesHashref;
  if ($matchesCount < $max_results) {
    my $page_data = get $solr_gene_url;
    unless ($page_data) { return $matchesHashref; }
    my $perl_scalar = $json->decode( $page_data );
    my %jsonHash = %$perl_scalar;

    foreach my $geneHash (@{ $jsonHash{"response"}{"docs"} }) {
      my %geneHash = %$geneHash;
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
    if (scalar (@{ $jsonHash{"response"}{"docs"} }) >= $max_results) { $$matchesHashref{"more results not shown; narrow your search"}++; }
  } # if (scalar keys %matches < $max_results)
  return $matchesHashref;
} # sub solrSearch


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
    <script type="text/javascript" src="../javascript/soba_biggo.js"></script>
EndOfText

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

  my $datatype = 'biggo';		# by defalt for front page
  my $solr_taxon_url = $base_solr_url . $datatype . '/select?qt=standard&fl=id,taxon,taxon_label&version=2.2&wt=json&rows=0&indent=on&q=*:*&facet=true&facet.field=taxon_label&facet.mincount=1&fq=document_category:%22bioentity%22';
  my $page_data = get $solr_taxon_url;
  my $perl_scalar = $json->decode( $page_data );
  my %jsonHash = %$perl_scalar;

  print qq(Select a datatype to display.<br/>\n);
  my @datatypes = qw( anatomy disease biggo go lifestage phenotype );
  foreach my $datatype (@datatypes) {
    my $checked = '';
    if ($datatype eq 'phenotype') { $checked = qq(checked="checked"); }
    print qq(<input type="radio" name="radio_datatype" id="radio_datatype" value="$datatype" $checked onclick="setAutocompleteListeners();" >$datatype</input><br/>\n); }

  print qq(<br/>Prioritize search by selecting one or more species.<br/>\n);
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

  print qq(</body></html>);
} # sub frontPage


sub calcNodeWidth {
  my ($nodeCount, $maxAnyCount) = @_;
  unless ($maxAnyCount) { $maxAnyCount = 1; }
  my $nodeWidth    = 1; my $nodeScale = 1.5; my $nodeMinSize = 0.01; my $logScaler = .6;
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
  $prevTime = $now;
  $message = qq($diffStart seconds from start, $diffPrev seconds from previous check.  Now $message);
  return ($message);
} # sub getDiffTime



sub calculateNodesAndEdges {
  my ($focusTermId, $datatype, $rootsChosen, $filterForLcaFlag, $maxDepth, $maxNodes) = @_;
  my (@parentNodes) = split/,/, $rootsChosen;
  unless ($datatype) { $datatype = 'phenotype'; }			# later will need to change based on different datatypes
#   if ($datatype eq 'phenotype') {		# FIX should come from function call
#     @parentNodes = ( 'WBPhenotype:0000886');	# TESTING , doesn't work 2019 03 01
#   }

# # radio_etgo=radio_etgo_withiea&rootsChosen=&maxNodes=0&maxDepth=0&filterLongestFlag=0&filterForLcaFlag=1
# # radio_etgo=radio_etgo_withiea&rootsChosen=                   &showControlsFlag=1&fakeRootFlag=0&filterForLcaFlag=1&filterLongestFlag=0&maxNodes=0&maxDepth=0
# # radio_etgo=             &rootsChosen=WBPhenotype:0000886&showControlsFlag=1               &filterForLcaFlag=0&filterLongestFlag=0&maxNodes=0&maxDepth=0

  my ($var, $radio_etgo)       = &getHtmlVar($query, 'radio_etgo');
  my ($var, $radio_etp)        = &getHtmlVar($query, 'radio_etp');
  my ($var, $radio_etd)        = &getHtmlVar($query, 'radio_etd');
  my ($var, $radio_eta)        = &getHtmlVar($query, 'radio_eta');
  my $toReturn = '';
  my $solr_url = $base_solr_url . $datatype . '/';
    # link 1, from wbgene get wbphenotypes from   "grouped":{ "annotation_class":{ "matches":12, "ngroups":4, "groups":[{ "groupValue":"WBPhenotype:0000674", # }]}}

  my %allLca;								# all nodes that are LCA to any pair of annotated terms
  my %nodes;
  my %edgesPtc;								# edges from parent to child

  my $nodeWidth    = 1;
  my $weightedNodeWidth    = 1;
  my $unweightedNodeWidth  = 1;

  my %annotationCounts;							# get annotation counts from evidence type
  my %phenotypes; my @annotPhenotypes;					# array of annotated terms to loop and do pairwise comparisons
  my $annotation_count_solr_url = $solr_url . 'select?qt=standard&indent=on&wt=json&version=2.2&rows=100000&fl=regulates_closure,id,annotation_class&q=document_category:annotation&fq=-qualifier:%22not%22&fq=bioentity:%22' . $focusTermId . '%22';
  if ($radio_etgo) {
    if ($radio_etgo eq 'radio_etgo_excludeiea') { $annotation_count_solr_url = $solr_url . 'select?qt=standard&indent=on&wt=json&version=2.2&rows=100000&fl=regulates_closure,id,annotation_class&q=document_category:annotation&fq=-qualifier:%22not%22&fq=-evidence_type:IEA&fq=bioentity:%22' . $focusTermId . '%22'; }
      elsif ($radio_etgo eq 'radio_etgo_onlyiea') { $annotation_count_solr_url = $solr_url . 'select?qt=standard&indent=on&wt=json&version=2.2&rows=100000&fl=bioentity,regulates_closure,id,annotation_class&q=document_category:annotation&fq=-qualifier:%22not%22&fq=evidence_type:(IDA+IEP+IGC+IGI+IMP+IPI)&fq=bioentity:%22' . $focusTermId . '%22'; } }
  if ($radio_etp) {
    if ($radio_etp eq 'radio_etp_onlyvariation') {  $annotation_count_solr_url = $solr_url . 'select?qt=standard&indent=on&wt=json&version=2.2&rows=100000&fl=regulates_closure,id,annotation_class&q=document_category:annotation&fq=-qualifier:%22not%22&fq=evidence_type:Variation&fq=bioentity:%22' . $focusTermId . '%22'; }
      elsif ($radio_etp eq 'radio_etp_onlyrnai') {  $annotation_count_solr_url = $solr_url . 'select?qt=standard&indent=on&wt=json&version=2.2&rows=100000&fl=regulates_closure,id,annotation_class&q=document_category:annotation&fq=-qualifier:%22not%22&fq=evidence_type:RNAi&fq=bioentity:%22' . $focusTermId . '%22'; } }
  if ($radio_etd) {
    if ($radio_etd eq 'radio_etd_excludeiea') { $annotation_count_solr_url = $solr_url . 'select?qt=standard&indent=on&wt=json&version=2.2&rows=100000&fl=regulates_closure,id,annotation_class&q=document_category:annotation&fq=-qualifier:%22not%22&fq=-evidence_type:IEA&fq=bioentity:%22' . $focusTermId . '%22'; } }
  if ($radio_eta) {
    if ($radio_eta eq 'radio_eta_onlyexprcluster') {       $annotation_count_solr_url = $solr_url . 'select?qt=standard&indent=on&wt=json&version=2.2&rows=100000&fl=regulates_closure,id,annotation_class&q=document_category:annotation&fq=-qualifier:%22not%22&fq=id:(*WB\:WBPaper*)&fq=bioentity:%22' . $focusTermId . '%22'; }
      elsif ($radio_eta eq 'radio_eta_onlyexprpattern') {  $annotation_count_solr_url = $solr_url . 'select?qt=standard&indent=on&wt=json&version=2.2&rows=100000&fl=regulates_closure,id,annotation_class&q=document_category:annotation&fq=-qualifier:%22not%22&fq=id:(*WB\:Expr*+*WB\:Marker*)&fq=bioentity:%22' . $focusTermId . '%22'; } }


# Anatomy, Expr and Expression_cluster (ref.
# https://wormbase.org/tools/ontology_browser/show_genes?focusTermName=Anatomy&focusTermId=WBbt:0005766).
# There are three groups of objects WB:Expr***, WBMarker*** (these are Expression patterns), WB:WBPaper*** (these are Expression profiles).

# amigo.cgi query
#   $annotation_count_solr_url = $solr_url . 'select?qt=standard&indent=on&wt=json&version=2.2&rows=100000&fl=regulates_closure,id,annotation_class&q=document_category:annotation&fq=-qualifier:%22not%22&fq=bioentity:%22WB:' . $focusTermId . '%22';

  my $page_data   = get $annotation_count_solr_url;                                           # get the URL
#   print qq( annotation_count_solr_url $annotation_count_solr_url\n);                                           # get the URL
# numFound == 0
  my $perl_scalar = $json->decode( $page_data );                        # get the solr data
  my %jsonHash    = %$perl_scalar;

  if ($jsonHash{'response'}{'numFound'} == 0) { return ($toReturn, \%nodes, \%nodes); }	# return nothing if there are no annotations found

  foreach my $doc (@{ $jsonHash{'response'}{'docs'} }) {
    my $phenotype = $$doc{'annotation_class'};
    $phenotypes{$phenotype}++;
    my $id = $$doc{'id'};
    my (@idarray) = split/\t/, $id;
    if ($datatype eq 'anatomy') {  
        my @entries = split/\|/, $idarray[7];
        foreach my $entry (@entries) { 
          my $type = ''; 
          if ($entry =~ m/^WB:Expr/) {         $type = 'Expression Pattern'; }
            elsif ($entry =~ m/^WBMarker/) {   $type = 'Expression Pattern'; }
            elsif ($entry =~ m/^WB:WBPaper/) { $type = 'Expression Cluster'; }
          if ($type) {
            foreach my $goid (@{ $$doc{'regulates_closure'} }) {
              $annotationCounts{$goid}{'any'}++; $annotationCounts{$goid}{$type}++; 
              $nodes{$goid}{'counts'}{'any'}++;  $nodes{$goid}{'counts'}{$type}++;  } } } }
      else {
        my $type = $idarray[6];
        if ($datatype eq 'lifestage') { if ($type eq 'IDA') { $type = 'Gene Expression'; } }
        foreach my $goid (@{ $$doc{'regulates_closure'} }) {
          $annotationCounts{$goid}{'any'}++; $annotationCounts{$goid}{$type}++; 
          $nodes{$goid}{'counts'}{'any'}++;  $nodes{$goid}{'counts'}{$type}++;  } }
  }


# amigo.cgi
#     my $annotation_count_solr_url = $solr_url . 'select?qt=standard&indent=on&wt=json&version=2.2&rows=100000&fl=regulates_closure,id,annotation_class&q=document_category:annotation&fq=-qualifier:%22not%22&fq=bioentity:%22WB:' . $focusTermId . '%22';
#     my $phenotype_solr_url = $solr_url . 'select?qt=standard&fl=regulates_transitivity_graph_json,topology_graph_json&version=2.2&wt=json&indent=on&rows=1&fq=-is_obsolete:true&fq=document_category:%22ontology_class%22&q=id:%22' . $phenotypeId . '%22';


  foreach my $phenotypeId (sort keys %phenotypes) {
    push @annotPhenotypes, $phenotypeId;
    my $phenotype_solr_url = $solr_url . 'select?qt=standard&fl=regulates_transitivity_graph_json,topology_graph_json&version=2.2&wt=json&indent=on&rows=1&fq=-is_obsolete:true&fq=document_category:%22ontology_class%22&q=id:%22' . $phenotypeId . '%22';

    my $page_data   = get $phenotype_solr_url;                                           # get the URL
#     print qq( phenotype_solr_url $phenotype_solr_url\n);                                           # get the URL
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
#       $lbl = "$id - $lbl";                                          # node label should have full id, not stripped of :, which is required for edge title text
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
#          my $url = "http://www.wormbase.org/species/all/go_term/$phenotype";                              # URL to link to wormbase page for object
           $allLca{$phenotype}++;
           unless ($phenotypes{$phenotype}) { 					# only add lca nodes that are not annotated terms
# print qq(NODES $phenotype LCA\n);
             $nodes{$phenotype}{lca}++; } } } }
    else {
      while (@annotPhenotypes) {
        my $ph1 = shift @annotPhenotypes;					# compare each annotated term node to all other annotated term nodes
#         my $url = "http://www.wormbase.org/species/all/go_term/$ph1";                              # URL to link to wormbase page for object
        my $xlabel = $ph1; 	# FIX
        $nodes{$ph1}{annot}++;
        foreach my $ph2 (@annotPhenotypes) {				# compare each annotated term node to all other annotated term nodes
          my $lcaHashref = &calculateLCA($ph1, $ph2);
          my %lca = %$lcaHashref;
          foreach my $lca (sort keys %lca) {
#             $url = "http://www.wormbase.org/species/all/go_term/$lca";                              # URL to link to wormbase page for object
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
  while (@parentNodes) {						# while there are parent nodes, go through them
    my $parent = shift @parentNodes;					# take a parent
    my %edgesPtcCopy = %{ dclone(\%edgesPtc) };				# make a temp copy since edges will be getting deleted per parent
    while (scalar keys %{ $edgesPtcCopy{$parent} } > 0) {		# while parent has children
      foreach my $child (sort keys %{ $edgesPtcCopy{$parent} }) {	# each child of parent
        if ($allLca{$child} || $phenotypes{$child}) { 			# good node, keep edge when child is an lca or annotated term
            delete $edgesPtcCopy{$parent}{$child};			# remove from %edgesPtc, does not need to be checked further
            push @parentNodes, $child;					# child is a good node, add to parent list to check its children
            $edgesLca{$parent}{$child}++; }				# add parent-child edge to final graph
          else {							# bad node, remove and reconnect edges
            delete $edgesPtcCopy{$parent}{$child};			# remove parent-child edge
            foreach my $grandchild (sort keys %{ $edgesPtcCopy{$child} }) {	# take each grandchild of child
              delete $edgesPtcCopy{$child}{$grandchild};		# remove child-grandchild edge
              $edgesPtcCopy{$parent}{$grandchild}++; } }		# make replacement edge between parent and grandchild
      } # foreach my $child (sort keys %{ $edgesPtcCopy{$parent} })
    } # while (scalar keys %{ $edgesPtcCopy{$parent} } > 0)
  } # while (@parentNodes)

  return ($toReturn, \%nodes, \%edgesLca);
} # sub calculateNodesAndEdges


sub annotSummaryJsonp {
  my ($var, $datatype)          = &getHtmlVar($query, 'datatype');
  ($var, my $callback)          = &getHtmlVar($query, 'callback');
# /~azurebrd/cgi-bin/amigo.cgi?action=annotSummaryJsonp&focusTermId=WBGene00000899
# for cross domain access, needs to be jsonp with header below, content-type is different, json has a function wrapped around it.
  print $query->header(
    -type => 'application/javascript',
    -access_control_allow_origin => '*',
  );
  if ($callback) { 									# Sibyl would like to assign the callback name as a parameter
      print qq($callback\(\n); }					
    else {
      my $ucfirstDatatype = ucfirst($datatype);
      print qq(jsonCallback$ucfirstDatatype\(\n); }					# need the datatype for separate widgets with different cytoscape graphs to tell which one they want back
  &annotSummaryJsonCode();
  print qq(\);\n);
} # sub annotSummaryJsonp

sub annotSummaryJson {			# temporarily keep this for the live www.wormbase going through the fake phenotype_graph_json widget
# /~azurebrd/cgi-bin/amigo.cgi?action=annotSummaryJson&focusTermId=WBGene00000899
  print qq(Content-type: application/json\n\n);		# for json
  &annotSummaryJsonCode();
} # sub annotSummaryJson

sub annotSummaryJsonCode {
  my ($var, $focusTermId)       = &getHtmlVar($query, 'focusTermId');
  my ($var, $datatype)          = &getHtmlVar($query, 'datatype');
  my ($var, $fakeRootFlag)      = &getHtmlVar($query, 'fakeRootFlag');
  my ($var, $filterLongestFlag) = &getHtmlVar($query, 'filterLongestFlag');
  my ($var, $filterForLcaFlag)  = &getHtmlVar($query, 'filterForLcaFlag');
  my ($var, $rootsChosen)       = &getHtmlVar($query, 'rootsChosen');
  my ($var, $maxNodes)          = &getHtmlVar($query, 'maxNodes');
  my ($var, $maxDepth)          = &getHtmlVar($query, 'maxDepth');
  ($datatype) = lc($datatype);
  unless ($maxNodes) { $maxNodes = 0; }
  unless ($maxDepth) { $maxDepth = 0; }
  unless ($rootsChosen) {
    if ($datatype eq 'phenotype')     { $rootsChosen = "WBPhenotype:0000886"; }
     elsif ($datatype eq 'anatomy')   { $rootsChosen = "WBbt:0000100";        }
     elsif ($datatype eq 'disease')   { $rootsChosen = "DOID:4";              }
     elsif ($datatype eq 'lifestage') { $rootsChosen = "WBls:0000075";        }
  }
  my (@rootsChosen) = split/,/, $rootsChosen;
  my ($return, $nodesHashref, $edgesLcaHashref) = &calculateNodesAndEdges($focusTermId, $datatype, $rootsChosen, $filterForLcaFlag, $maxDepth, $maxNodes);
  if ($return) { print qq(RETURN $return ENDRETURN\n); }
  my %nodes    = %$nodesHashref;
  my %edgesLca = %$edgesLcaHashref;
  if ($fakeRootFlag) { 
    if ( ($datatype eq 'go') || ($datatype eq 'biggo') ) {
      my $fakeRoot = 'GO:0000000';
      $nodes{$fakeRoot}{label} = 'Gene Ontology';
      $nodesAll{$fakeRoot}{label} = 'Gene Ontology';
      foreach my $sub (@rootsChosen) {
        if ($nodes{$sub}{'counts'}) {					# root must have an annotation to be added
          $edgesLca{$fakeRoot}{$sub}++; }				# any existing edge, parent to child 
  } } }
  my @nodes = ();
  my %rootNodes; 
  my $rootNodeMaxAnnotationCount = 1;					# max annotation count to calculate node size
  foreach my $root (@rootsChosen) { 
    $rootNodes{$root}++; 						# add to roots hash
    if ($nodes{$root}{'counts'}{'any'}) {				# find maximum annotation count among roots
      if ($nodes{$root}{'counts'}{'any'} > $rootNodeMaxAnnotationCount) { 
        $rootNodeMaxAnnotationCount = $nodes{$root}{'counts'}{'any'}; } } }
  if ($fakeRootFlag) { 
    if ( ($datatype eq 'go') || ($datatype eq 'biggo') ) {
      $rootNodes{'GO:0000000'}++; } }
  my $diameterMultiplier = 60;

  my %edgesFromLongest;							# find edges that belong to the longest path from all nodes to each of their children (to remove indirect nodes, like a grandchild directly to the grandparent, bypassing the parent)
  foreach my $source (sort keys %nodes) {				# for all nodes, calculate longest paths to each child and add to %edgesFromLongest
    foreach my $target (sort keys %{ $edgesLca{$source } }) {
      %paths = ();
      foreach my $source (sort keys %edgesLca) {
        foreach my $target (sort keys %{ $edgesLca{$source } }) {
          $paths{"childToParent"}{$target}{$source}++; } }
      my ($edgesFromFinalPathHashref) = &getLongestPathAndTransitivity($source, $target);
      my %edgesFromFinalPath = %$edgesFromFinalPathHashref;
      foreach my $source (sort keys %{ $edgesFromFinalPath{'longest'} }) {
        foreach my $target (sort keys %{ $edgesFromFinalPath{'longest'}{$source} }) {
          $edgesFromLongest{$source}{$target}++; } }
    } # foreach my $target (sort keys %{ $edgesLca{$source } })
  } # foreach my $source (sort keys %nodes) 

  if ($filterLongestFlag) {						# remove edges of non-longest path, which are redundant
    my %tempEdges;
    foreach my $source (sort keys %edgesLca) {
      foreach my $target (sort keys %{ $edgesLca{$source } }) {
        if ($edgesFromLongest{$target}{$source}) { $tempEdges{$source}{$target} = $edgesLca{$source}{$target}; } } }
    %edgesLca = %{ dclone(\%tempEdges) }; }

  my %edgesAfterLongestBeforeLopping = %{ dclone(\%edgesLca) };
  my %nodesAfterLongestBeforeLopping = %{ dclone(\%nodes) };

# Lopping top layers to less than maxNodes
  if ($maxNodes) {							# only show up to maxNodes amount of nodes
    my $count = 0;
    my %tempNodes; my %tempEdges;
    my %lastGoodNodes; my %lastGoodEdges;
    my (@parentNodes) = split/,/, $rootsChosen;
    if ($fakeRootFlag) { @parentNodes = ( 'GO:0000000' ); $maxNodes++; }
    
    foreach my $node (@parentNodes) {
#       $count++;
# print qq(NODE $node COUNT $count\n);
      foreach my $type (keys %{ $nodes{$node} }) {
        $tempNodes{$node}{$type} = $nodes{$node}{$type}; } }
    my @nextLayerParentNodes = ();
    while ( (scalar @parentNodes > 0) && ($count < $maxNodes) ) {						# while there are parent nodes, go through them
      my $parent = shift @parentNodes;					# take a parent
      foreach my $child (sort keys %{ $edgesLca{$parent} }) {		# each child of parent
        $tempEdges{$parent}{$child}++;					# add parent-child edge to final graph
        next if (exists $tempNodes{$child});				# skip children already added through other parent
        $count++;
        if ($parent eq 'GO:0000000') { $count--; }			# never count nodes attached to fake root
# print qq(NODE CHILD $child PARENT $parent COUNT $count\n);
        foreach my $type (keys %{ $nodes{$child} }) {
          $tempNodes{$child}{$type} = $nodes{$child}{$type}; }
        push @nextLayerParentNodes, $child;					# child is a good node, add to parent list to check its children
      } # foreach my $child (sort keys %{ $edgesLca{$parent} })
      if ( (scalar @parentNodes == 0) && ($count < $maxNodes) ) {
        @parentNodes = @nextLayerParentNodes;
        @nextLayerParentNodes = ();
#         print qq(NODE COUNT $count\n);
        %lastGoodNodes = %{ dclone(\%tempNodes) };
        %lastGoodEdges = %{ dclone(\%tempEdges) };
      }
    } # while (@parentNodes)
#     %nodes = %{ dclone(\%tempNodes) };
#     %edgesLca = %{ dclone(\%tempEdges) };
    %nodes = %{ dclone(\%lastGoodNodes) };
    %edgesLca = %{ dclone(\%lastGoodEdges) };
  } # if ($maxNodes)

  my $fullDepthFlag = 1;						# calculate the full depth from the graph after lca and longest path
  my $fullDepth = 10;							# initialize to some large depth just in case
  if ($fullDepthFlag) {
    my $nodeDepth = 1;
    my %tempNodes; my %tempEdges;
    my %lastGoodNodes; my %lastGoodEdges;
    my (@parentNodes) = split/,/, $rootsChosen;
    if ($fakeRootFlag) { 
      if ( ($datatype eq 'go') || ($datatype eq 'biggo') ) {
        @parentNodes = ( 'GO:0000000' ); $nodeDepth = 0; } }
    
    foreach my $node (@parentNodes) {
# print qq(NODE $node PN @parentNodes\n);
      foreach my $type (keys %{ $nodes{$node} }) {
        $tempNodes{$node}{$type} = $nodes{$node}{$type}; } }
    if ($maxDepth) {						# if there's a max depth requested
      if ($nodeDepth == $maxDepth) {				# if requested depth is current depth, save the nodes and edges
        %lastGoodNodes = %{ dclone(\%tempNodes) };		# doing this here in the case user wants max depth of 1
        %lastGoodEdges = %{ dclone(\%tempEdges) }; } }
    my @nextLayerParentNodes = ();
    while ( (scalar @parentNodes > 0) ) {						# while there are parent nodes, go through them
# print qq(MAX DEPTH $maxDepth<BR>\n);
# print qq(NODE DEPTH $nodeDepth<BR>\n);
      my $parent = shift @parentNodes;					# take a parent
# print qq(PARENT $parent PN @parentNodes\n);
      foreach my $child (sort keys %{ $edgesLca{$parent} }) {		# each child of parent
        $tempEdges{$parent}{$child}++;					# add parent-child edge to final graph
        next if (exists $tempNodes{$child});				# skip children already added through other parent
#         $count++;
#         if ($parent eq 'GO:0000000') { $count--; }			# never count nodes attached to fake root
# print qq(NODE CHILD $child PARENT $parent\n);
        foreach my $type (keys %{ $nodes{$child} }) {
          $tempNodes{$child}{$type} = $nodes{$child}{$type}; }
        push @nextLayerParentNodes, $child;					# child is a good node, add to parent list to check its children
# print qq(ADD $child to next layer\n);
      } # foreach my $child (sort keys %{ $edgesLca{$parent} }) 
      if ( (scalar @parentNodes == 0) ) {				# if looked at all parent nodes
# print qq(DEPTH INCREASE\n);
        $nodeDepth++;							# increase depth
        @parentNodes = @nextLayerParentNodes;				# repopulate from the next layer of parent nodes
        @nextLayerParentNodes = ();					# clean up the next layer of parent nodes
#         print qq(NODE DEPTH $nodeDepth\n);
        if ($maxDepth) {						# if there's a max depth requested
          if ($nodeDepth == $maxDepth) {				# if requested depth is current depth, save the nodes and edges
            %lastGoodNodes = %{ dclone(\%tempNodes) };
            %lastGoodEdges = %{ dclone(\%tempEdges) }; } } }
    } # while (@parentNodes)
    $fullDepth = $nodeDepth - 1;					# node depth went one too many
    unless ($maxDepth) {						# if there's no max depth, use the full graph
      %lastGoodNodes = %{ dclone(\%tempNodes) };
      %lastGoodEdges = %{ dclone(\%tempEdges) }; }
    %nodes = %{ dclone(\%lastGoodNodes) };
    %edgesLca = %{ dclone(\%lastGoodEdges) };
  } # if ($fullDepthFlag)


    # 2019 01 29 some nodes have connection to parents in the graph at the same level, but the edges are removed in lopping because lopping doesn't keep going lower.
    # e.g. /~raymond/cgi-bin/soba_biggo.cgi?action=annotSummaryCytoscape&autocompleteValue=F56F4.3%20(Caenorhabditis%20elegans,%20WB:WBGene00018980,%20-,%20-)&showControlsFlag=1  max nodes 10  5887 -> 16021  gone despite both being in graph, so that it limits edges down to lowest number.
  my $addEdgesOfNodesToParentsDirectlyInTheGraph = 1;
  if ($addEdgesOfNodesToParentsDirectlyInTheGraph) {			
    foreach my $nodeInGraph (sort keys %nodes) {
#       print qq(NODE $nodeInGraph NODE\n);
      foreach my $child (sort keys %{ $edgesAfterLongestBeforeLopping{$nodeInGraph} }) {
        if ($nodes{$child}) {
          $edgesLca{$nodeInGraph}{$child}++;					# add parent-child edge to final graph
        }
      } # foreach my $child (sort keys %{ $edgesAfterLongestBeforeLopping{$nodeInGraph} })
    }
  }

    # 2019 01 29, Raymond suggests if nodes have parent that are not on the graph, follow those parents to their parents until there's a parent in the graph and add an edge there.
  my $addEdgesOfNodesToLowestAncestorsInTheGraph = 1;
  if ($addEdgesOfNodesToLowestAncestorsInTheGraph) {
    my %edgesAfterLongestBeforeLoppingChildToParent;
    foreach my $parent (keys %edgesAfterLongestBeforeLopping) {
      foreach my $child (keys %{ $edgesAfterLongestBeforeLopping{$parent} }) {
# if ($child eq 'GO:0005310') { print qq(edgesAfterLongestBeforeLoppingChildToParent CHILD $child PARENT $parent E<br>\n); }
        $edgesAfterLongestBeforeLoppingChildToParent{$child}{$parent}++; } }
    my %tempEdges = %{ dclone(\%edgesLca) };
    foreach my $nodeInGraph (sort keys %nodes) {
      my $tempEdgesHref = &recurseAncestorsToAddEdges($nodeInGraph, $nodeInGraph, \%edgesAfterLongestBeforeLoppingChildToParent, \%tempEdges, \%nodes);
      %tempEdges = %$tempEdgesHref;
    } # foreach my $nodeInGraph (sort keys %nodes)
    %edgesLca = %{ dclone(\%tempEdges) };
  }

#   my $threshold = 40;
#   my %nodesUnderThreshold; my %edgesUnderThreshold;
 
  my @edges = ();
  my %nodesWithEdges;
  foreach my $source (sort keys %edgesLca) {
    foreach my $target (sort keys %{ $edgesLca{$source } }) {
      my $lineColor = '#ddd'; if ($source eq 'GO:0000000') { $lineColor = '#fff'; }
      my $cSource = $source;		# $cSource =~ s/GO://;
      my $cTarget = $target;		# $cTarget =~ s/GO://;
      my $cSourceColonless = $cSource;      $cSourceColonless =~ s/://;	
      my $cTargetColonless = $cTarget;      $cTargetColonless =~ s/://;	


# FIX tracking if needs prefix
      $nodesWithEdges{"$cSource"}++; $nodesWithEdges{"$cTarget"}++;
#       $nodesWithEdges{"GO:$cSource"}++; $nodesWithEdges{"GO:$cTarget"}++;
      my $name = $cSourceColonless . $cTargetColonless;
# print qq(SOURCE $source TARGET $target E\n);
      push @edges, qq({ "data" : { "id" : "$name", "weight" : 1, "source" : "$cSourceColonless", "target" : "$cTargetColonless", "lineColor" : "$lineColor" } }); } }
  my $edges = join",\n", @edges; 

  my %goslimIds;
  if ( ($datatype eq 'go') || ($datatype eq 'biggo') ) {
    my ($goslimIdsRef) = &getGoSlimGoids($datatype);
    %goslimIds = %$goslimIdsRef; }

  foreach my $node (sort keys %nodes) {
    next unless ( ($nodesWithEdges{$node}) || ($maxDepth == 1) );	# nodes must have an edge unless the depth is only 1
    my $name = $nodes{$node}{label};
    $name =~ s/ /\\n/g;							# to add linebreaks to node labels
    my @annotCounts;
    foreach my $evidenceType (sort keys %{ $nodes{$node}{'counts'} }) {
      next if ($evidenceType eq 'any');				# skip 'any', only used for relative size to max value
      push @annotCounts, qq($nodes{$node}{'counts'}{$evidenceType} $evidenceType); }
    my $annotCounts = join"; ", @annotCounts;
    my $diameter = $diameterMultiplier * &calcNodeWidth($nodes{$node}{'counts'}{'any'}, $rootNodeMaxAnnotationCount);
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
    my $nodeExpandable = 'false'; 
# label nodes green if they have a child it could expand into, not relevant 2019 02 08
#     foreach my $child (sort keys %{ $edgesLca{$node} }) {               # each child of node
# # print qq(NODE $node CHILD $child HAS $nodes{$child}{label} E<br>\n);
#       unless ($nodes{$child}{label}) { 
# # print qq(BLANK NODE $node CHILD $child HAS $nodes{$child}{label} E<br>\n);
#         $labelColor = 'green';
#         $nodeExpandable = 'true'; 
#     } }

    my $cytId = $node; $cytId =~ s/://;
    if ($rootNodes{$node}) {
      next unless ($nodes{$node}{'counts'});			# only add a root if it has annotations
      my $nodeColor  = 'blue';  if ($node eq 'GO:0000000') { $nodeColor  = '#fff'; }
      if ($goslimIds{$node}) { $backgroundColor = $nodeColor; }
# print qq(ROOT NODE $node\n);
#         $node =~ s/GO://; 
        push @nodes, qq({ "data" : { "id" : "$cytId", "objId" : "$node", "name" : "$name", "annotCounts" : "$annotCounts", "borderStyle" : "dashed", "labelColor" : "$labelColor", "nodeColor" : "$nodeColor", "annotationDirectness" : "inferred", "borderWidthUnweighted" : "$borderWidthRoot_unweighted", "borderWidthWeighted" : "$borderWidthRoot_weighted", "borderWidth" : "$borderWidthRoot", "fontSizeUnweighted" : "$fontSize_unweighted", "fontSizeWeighted" : "$fontSize_weighted", "fontSize" : "$fontSize", "diameter" : $diameter, "diameter_weighted" : $diameter_weighted, "diameter_unweighted" : $diameter_unweighted, "backgroundColor" : "$backgroundColor", "nodeShape" : "rectangle", "nodeExpandable" : "$nodeExpandable" } }); }
      elsif ($nodes{$node}{lca}) {
# print qq(LCA NODE $node\n);
        if ($goslimIds{$node}) { $backgroundColor = 'blue'; }
#         $node =~ s/GO://; 
        push @nodes, qq({ "data" : { "id" : "$cytId", "objId" : "$node", "name" : "$name", "annotCounts" : "$annotCounts", "borderStyle" : "dashed", "labelColor" : "$labelColor", "nodeColor" : "blue", "annotationDirectness" : "inferred", "borderWidthUnweighted" : "$borderWidth_unweighted", "borderWidthWeighted" : "$borderWidth_weighted", "borderWidth" : "$borderWidth", "fontSizeUnweighted" : "$fontSize_unweighted", "fontSizeWeighted" : "$fontSize_weighted", "fontSize" : "$fontSize", "diameter" : $diameter, "diameter_weighted" : $diameter_weighted, "diameter_unweighted" : $diameter_unweighted, "backgroundColor" : "$backgroundColor", "nodeShape" : "ellipse", "nodeExpandable" : "$nodeExpandable" } });   }
      elsif ($nodes{$node}{annot}) {
# print qq(ANNOT NODE $node\n);
         if ($goslimIds{$node}) { $backgroundColor = 'red'; }
#          $node =~ s/GO://; 
         push @nodes, qq({ "data" : { "id" : "$cytId", "objId" : "$node", "name" : "$name", "annotCounts" : "$annotCounts", "borderStyle" : "solid", "labelColor" : "$labelColor", "nodeColor" : "red", "annotationDirectness" : "direct", "borderWidthUnweighted" : "$borderWidth_unweighted", "borderWidthWeighted" : "$borderWidth_weighted", "borderWidth" : "$borderWidth", "fontSizeUnweighted" : "$fontSize_unweighted", "fontSizeWeighted" : "$fontSize_weighted", "fontSize" : "$fontSize", "diameter" : $diameter, "diameter_weighted" : $diameter_weighted, "diameter_unweighted" : $diameter_unweighted, "backgroundColor" : "$backgroundColor", "nodeShape" : "ellipse", "nodeExpandable" : "$nodeExpandable" } });     } 
      else {
# print qq(OTHER NODE $node\n); 
    }
  }

  unless (scalar @nodes > 0) { 
    if ($fakeRootFlag) { 
      if ( ($datatype eq 'go') || ($datatype eq 'biggo') ) {
        push @nodes, qq({ "data" : { "id" : "GO:0000000", "name" : "Gene Ontology", "annotCounts" : "", "borderStyle" : "dashed", "labelColor" : "#888", "nodeColor" : "#888", "borderWidthUnweighted" : "8", "borderWidthWeighted" : "8", "borderWidth" : "8", "fontSizeUnweighted" : "6", "fontSizeWeighted" : "4", "fontSize" : "4", "diameter" : 0.6, "diameter_weighted" : 0.6, "diameter_unweighted" : 40, "backgroundColor" : "white", "nodeShape" : "rectangle" } }); } } }

  unless (scalar @nodes > 0) { 
    push @nodes, qq({ "data" : { "id" : "No Annotations", "name" : "No Annotations", "annotCounts" : "1", "borderStyle" : "dashed", "labelColor" : "#888", "nodeColor" : "#888", "borderWidthUnweighted" : "8", "borderWidthWeighted" : "8", "borderWidth" : "8", "fontSizeUnweighted" : "6", "fontSizeWeighted" : "4", "fontSize" : "4", "diameter" : 0.6, "diameter_weighted" : 0.6, "diameter_unweighted" : 40, "backgroundColor" : "white", "nodeShape" : "rectangle" } }); }

  my $ucfirstDatatype = ucfirst($datatype);
  my $nodes = join",\n", @nodes; 
  print qq({ "elements" : {\n);
  print qq("nodes" : [\n);
  print qq($nodes\n);
  print qq(],\n);
  print qq("edges" : [\n);
  print qq($edges\n);
  print qq(]\n);
  print qq(, "meta" : { "fullDepth" : $fullDepth, "focusTermId" : "$focusTermId", "urlBase" : "https://${hostname}.caltech.edu/~raymond/cgi-bin/soba_biggo.cgi?action=annotSummaryJsonp&focusTermId=${focusTermId}&datatype=${ucfirstDatatype}" } } }\n);
} # sub annotSummaryJsonCode

sub recurseAncestorsToAddEdges {		# for a given node in the graph after longest path and trimming, check its parents, if a parent is in the graph then link it to the given node, otherwise check the grandparents to link to original node, recurse.
  my ($focusNode, $originalNode, $edgesAfterLongestBeforeLoppingChildToParentHref, $tempEdgesHref, $nodesInGraphHref) = @_;
  my %edgesAfterLongestBeforeLoppingChildToParent = %$edgesAfterLongestBeforeLoppingChildToParentHref;
  my %tempEdges = %$tempEdgesHref;
  my %nodesInGraph = %$nodesInGraphHref;
  foreach my $parent (sort keys %{ $edgesAfterLongestBeforeLoppingChildToParent{$focusNode} }) {
# if ($originalNode eq 'GO:0005310') { 
#   print qq(NODE O $originalNode F $focusNode P $parent E<br>\n); 
# }
    if ($nodesInGraph{$parent}) { 
# if ($originalNode eq 'GO:0005310') { 
#   print qq(NODE O $originalNode F $focusNode P $parent ADDING $parent TO $originalNode E<br>\n); 
# }
        $tempEdges{$parent}{$originalNode}++; 
        return \%tempEdges; }
      else {
# if ($originalNode eq 'GO:0005310') { 
#   print qq(NODE O $originalNode F $focusNode P $parent PARENT NOT IN GRAPH RECURSE<br>\n); 
# }
        my $tempEdgesHref = &recurseAncestorsToAddEdges($parent, $originalNode, \%edgesAfterLongestBeforeLoppingChildToParent, \%tempEdges, \%nodesInGraph);
        return $tempEdgesHref; }
  }
  return \%tempEdges;
} # sub recurseAncestorsToAddEdges 


sub getGoSlimGoids {
  my ($datatype) = @_;
  my %goslimIds;
  my $goslimUrl = $base_solr_url . $datatype . '/select?qt=standard&fl=id,annotation_class_label,topology_graph_json,subset&version=2.2&wt=json&indent=on&rows=1000&q=*:*&fq=document_category:%22ontology_class%22&fq=subset:%22goslim_agr%22';
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
# /~azurebrd/cgi-bin/amigo.cgi?action=annotSummaryCytoscape&focusTermId=WBGene00000899
  my ($all_roots) = @_;
  my ($var, $focusTermId)          = &getHtmlVar($query, 'focusTermId');
  ($var, my $autocompleteValue)    = &getHtmlVar($query, 'autocompleteValue');
  ($var, my $datatype)             = &getHtmlVar($query, 'datatype');
  ($var, my $showControlsFlag)     = &getHtmlVar($query, 'showControlsFlag');
  ($var, my $fakeRootFlag)         = &getHtmlVar($query, 'fakeRootFlag');
  ($var, my $filterLongestFlag)    = &getHtmlVar($query, 'filterLongestFlag');
  ($var, my $filterForLcaFlag)     = &getHtmlVar($query, 'filterForLcaFlag');
  ($var, my $maxNodes)             = &getHtmlVar($query, 'maxNodes');
  ($var, my $maxDepth)             = &getHtmlVar($query, 'maxDepth');
  ($var, my $nodeCountFlag)        = &getHtmlVar($query, 'nodeCountFlag');
  ($var, my $descriptionTerms)     = &getHtmlVar($query, 'descriptionTerms');
  ($var, my $radio_etgo)           = &getHtmlVar($query, 'radio_etgo');
  ($var, my $radio_etp)            = &getHtmlVar($query, 'radio_etp');
  ($var, my $radio_etd)            = &getHtmlVar($query, 'radio_etd');
  ($var, my $radio_eta)            = &getHtmlVar($query, 'radio_eta');
  ($var, my $root_bp)              = &getHtmlVar($query, 'root_bp');
  ($var, my $root_mf)              = &getHtmlVar($query, 'root_mf');
  ($var, my $root_cc)              = &getHtmlVar($query, 'root_cc');
  my $toPrint = ''; my $return = '';
  my $checked_radio_etp_all      = 'checked="checked"'; my $checked_radio_etp_onlyrnai = '';    my $checked_radio_etp_onlyvariation = '';
  if ($radio_etp eq 'radio_etp_onlyvariation') { $checked_radio_etp_all = ''; $checked_radio_etp_onlyvariation = 'checked="checked"'; }
    elsif ($radio_etp eq 'radio_etp_onlyrnai') { $checked_radio_etp_all = ''; $checked_radio_etp_onlyrnai      = 'checked="checked"'; }
  my $checked_radio_etd_all      = 'checked="checked"'; my $checked_radio_etd_excludeiea = '';    
  if ($radio_etd eq 'radio_etd_excludeiea') { $checked_radio_etd_all = ''; $checked_radio_etd_excludeiea = 'checked="checked"'; }
  my $checked_radio_etgo_withiea = 'checked="checked"'; my $checked_radio_etgo_excludeiea = ''; my $checked_radio_etgo_onlyiea = '';
  if ($radio_etgo eq 'radio_etgo_excludeiea') {   $checked_radio_etgo_withiea = ''; $checked_radio_etgo_excludeiea = 'checked="checked"'; }
    elsif ($radio_etgo eq 'radio_etgo_onlyiea') { $checked_radio_etgo_withiea = ''; $checked_radio_etgo_onlyiea    = 'checked="checked"'; }
  my $checked_radio_eta_all      = 'checked="checked"'; my $checked_radio_eta_onlyexprcluster = '';    my $checked_radio_eta_onlyexprpattern = '';
  if ($radio_eta eq 'radio_eta_onlyexprpattern') {      $checked_radio_eta_all = ''; $checked_radio_eta_onlyexprpattern = 'checked="checked"'; }
    elsif ($radio_eta eq 'radio_eta_onlyexprcluster') { $checked_radio_eta_all = ''; $checked_radio_eta_onlyexprcluster = 'checked="checked"'; }
  my $checked_root_bp = ''; my $checked_root_cc = ''; my $checked_root_mf = ''; 
  my @roots;
  if ( ($datatype eq 'go') || ($datatype eq 'biggo') ) {
     if ($all_roots eq 'all_roots') { 
         $fakeRootFlag = 0; $filterLongestFlag = 1; $filterForLcaFlag = 1; $maxNodes = 0; $maxDepth = 0;
         push @roots, "GO:0008150"; push @roots, "GO:0005575"; push @roots, "GO:0003674";
         $checked_root_bp = 'checked="checked"'; $checked_root_cc = 'checked="checked"'; $checked_root_mf = 'checked="checked"'; }
       else {
         if ($root_bp) { $checked_root_bp = 'checked="checked"'; push @roots, $root_bp; }
         if ($root_cc) { $checked_root_cc = 'checked="checked"'; push @roots, $root_cc; }
         if ($root_mf) { $checked_root_mf = 'checked="checked"'; push @roots, $root_mf; } } }
    elsif ($datatype eq 'phenotype') { push @roots, "WBPhenotype:0000886"; }
    elsif ($datatype eq 'anatomy')   { push @roots, "WBbt:0000100";        }
    elsif ($datatype eq 'disease')   { push @roots, "DOID:4";              }
    elsif ($datatype eq 'lifestage') { push @roots, "WBls:0000075";        }
  my $roots = join",", @roots;

  unless ($focusTermId) {
    ($focusTermId) = $autocompleteValue =~ m/, (.*?),/;
  }

  my $goslimButtons = '<a href="http://geneontology.org/docs/go-subset-guide/" target="_blank">Alliance Slim terms</a> in graph:<br/>';
  my %goslimIds;
  if ( ($datatype eq 'go') || ($datatype eq 'biggo') ) {
    my ($goslimIdsRef) = &getGoSlimGoids($datatype);
    %goslimIds = %$goslimIdsRef;
    foreach my $goid (sort keys %goslimIds) {
      my $goname = $goslimIds{$goid};
#       $goid =~ s/GO://;
      my $button      = qq(<span id="$goid" style="display: none">- $goname<br/></span>);
      $goslimButtons .= qq($button);
    } # foreach my $goid (sort keys %goslimIds)
  }

# FIX

  my $jsonUrl = 'soba_biggo.cgi?action=annotSummaryJson&focusTermId=' . $focusTermId . '&datatype=' . $datatype;
  if ( ($datatype eq 'go') || ($datatype eq 'biggo') ) { $jsonUrl .= '&radio_etgo=' . $radio_etgo . '&rootsChosen=' . $roots; }
    elsif ($datatype eq 'phenotype') {                   $jsonUrl .= '&radio_etp='  . $radio_etp;                             }
    elsif ($datatype eq 'disease') {                     $jsonUrl .= '&radio_etd='  . $radio_etd;                             }
    elsif ($datatype eq 'anatomy') {                     $jsonUrl .= '&radio_eta='  . $radio_eta;                             }
  unless ($showControlsFlag) { $showControlsFlag = 0; }
  $jsonUrl .= "&showControlsFlag=$showControlsFlag";
  unless ($fakeRootFlag) { $fakeRootFlag = 0; }
  $jsonUrl .= "&fakeRootFlag=$fakeRootFlag";
  unless ($filterForLcaFlag) { $filterForLcaFlag = 0; }
  $jsonUrl .= "&filterForLcaFlag=$filterForLcaFlag";
  unless ($filterLongestFlag) { $filterLongestFlag = 0; }
  $jsonUrl .= "&filterLongestFlag=$filterLongestFlag";
  unless ($maxNodes) { $maxNodes = 0; }
  $jsonUrl .= "&maxNodes=$maxNodes";
  unless ($maxDepth) { $maxDepth = 0; }
  $jsonUrl .= "&maxDepth=$maxDepth";
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
<link href="/~azurebrd/work/cytoscape/style.css" rel="stylesheet" />
<link href="https://cdnjs.cloudflare.com/ajax/libs/qtip2/2.2.0/jquery.qtip.min.css" rel="stylesheet" type="text/css" />
<meta charset=utf-8 />
<meta name="viewport" content="user-scalable=no, initial-scale=1.0, minimum-scale=1.0, maximum-scale=1.0, minimal-ui">
<title>$focusTermId Cytoscape view</title>


<script src="https://code.jquery.com/jquery-2.1.0.min.js"></script>

<script src="/~azurebrd/javascript/cytoscape.min.js"></script>

<script src="/~azurebrd/javascript/dagre.min.js"></script>
<script src="https://cdn.rawgit.com/cytoscape/cytoscape.js-dagre/1.1.2/cytoscape-dagre.js"></script>

<script src="https://cdnjs.cloudflare.com/ajax/libs/qtip2/2.2.0/jquery.qtip.min.js"></script>
<script src="https://cdn.rawgit.com/cytoscape/cytoscape.js-qtip/2.2.5/cytoscape-qtip.js"></script>

<script type="text/javascript">
\$(function(){
  // get exported json from cytoscape desktop via ajax
  var graphP = \$.ajax({
    url: '$jsonUrl',
    type: 'GET',
    dataType: 'json'
  });

  Promise.all([ graphP ]).then(initCy);

  function linkFromEdge(nodeObjId) {		// generate url from datatype + edge's target node's objId
    var linkout = '';
    if ('$datatype' === 'anatomy') {          linkout = 'https://wormbase.org/species/all/anatomy_term/' + nodeObjId + '#4--10'; }
      else if ('$datatype' === 'disease') {   linkout = 'https://wormbase.org/resources/disease/' + nodeObjId + '#2--10';        }
      else if ('$datatype' === 'go') {        linkout = 'https://wormbase.org/species/all/go_term/' + nodeObjId + '#2--10';      }
      else if ('$datatype' === 'lifestage') { linkout = 'https://wormbase.org/species/all/life_stage/' + nodeObjId + '#2--10';   }
      else if ('$datatype' === 'phenotype') { linkout = 'https://wormbase.org/species/all/phenotype/' + nodeObjId + '#3--10';    }
      else if ('$datatype' === 'biggo') {     linkout = '';      							      }
    return linkout;
  }

  function linkFromNode(nodeId) {		// generate url from datatype + nodeId
    var linkout = 'http://amigo.geneontology.org/amigo/term/' + nodeId;
    if ('$datatype' === 'anatomy') {          linkout = 'https://wormbase.org/species/all/anatomy_term/' + nodeId; }
      else if ('$datatype' === 'disease') {   linkout = 'https://wormbase.org/resources/disease/' + nodeId;        }
      else if ('$datatype' === 'go') {        linkout = 'https://wormbase.org/species/all/go_term/' + nodeId;      }
      else if ('$datatype' === 'lifestage') { linkout = 'https://wormbase.org/species/all/life_stage/' + nodeId;   }
      else if ('$datatype' === 'phenotype') { linkout = 'https://wormbase.org/species/all/phenotype/' + nodeId;    }
      else if ('$datatype' === 'biggo') {     linkout = 'http://amigo.geneontology.org/amigo/term/' + nodeId;      }
    return linkout;
  }

  function initCy( then ){
    var elements = then[0].elements;
    \$('#controldiv').show(); \$('#loadingdiv').hide();	// show controls and hide loading when graph loaded
    if ( ('$datatype' === 'go') || ('$datatype' === 'biggo') ) {
        \$('#trAllianceSlimWith').show(); 
        \$('#trAllianceSlimWithout').show(); 
        \$('#evidencetypego').show(); 
        \$('#goSlimDiv').show(); 
        \$('#rootschosen').show(); }
      else if ( '$datatype' === 'disease') { 
        \$('#evidencetypedisease').show(); }
      else if ( '$datatype' === 'phenotype') { 
        \$('#evidencetypephenotype').show(); }
      else if ( '$datatype' === 'anatomy') { 
        \$('#evidencetypeanatomy').show(); }
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
//             'min-zoomed-font-size': 8,		// FIX PUT THIS BACK
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

//         var maxOption = 7;
        var maxOption = then[0].elements.meta.fullDepth;
        document.getElementById('maxDepth').options.length = 0;
        for( var i = 1; i <= maxOption; i++ ){
          var label = i; 
//           if ((i == 0) || (i == maxOption)) { label = 'max'; }
          document.getElementById('maxDepth').options[i-1] = new Option(label, i, true, false) }
        document.getElementById('maxDepth').selectedIndex = maxOption - 1;

        cyPhenGraph.on('mouseover', 'edge', function(e){
          var edge        = e.cyTarget; 
          var nodeId      = edge.data('target');
          var nodeObj     = cyPhenGraph.getElementById( nodeId );
          var nodeObjId   = nodeObj.data('objId');
          var nodeName    = nodeObj.data('name');
          var linkout     = linkFromEdge(nodeObjId);
          var qtipContent = 'No information';
          if (linkout) { qtipContent = 'Explore <a target="_blank" href="' + linkout + '">' + nodeName + '</a> graph'; }
          edge.qtip({
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
        
        cyPhenGraph.on('tap', 'node', function(e){
          var node         = e.cyTarget; 
          var nodeId       = node.data('id');
          var neighborhood = node.neighborhood().add(node);
          cyPhenGraph.elements().addClass('faded');
          neighborhood.removeClass('faded');
//           if (node.data('nodeExpandable') === 'true') { alert(nodeId); }

          var node = e.cyTarget;
          var nodeId   = node.data('id');
          var objId    = node.data('objId');
          var nodeName = node.data('name');
          var annotCounts = node.data('annotCounts');
          var linkout = linkFromNode(objId);
          var qtipContent = 'Annotation Count:<br/>' + annotCounts + '<br/><a target="_blank" href="' + linkout + '">' + objId + ' - ' + nodeName + '</a>';
//           var qtipContent = annotCounts + '<br/><a target="_blank" href="http://amigo.geneontology.org/amigo/term/' + nodeId + '">' + nodeId + ' - ' + nodeName + '</a>';
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
            var objId    = node.data('objId');
            var nodeId   = node.data('id');
            var nodeName = node.data('name');
            var annotCounts = node.data('annotCounts');
            var linkout = linkFromNode(objId);
            var qtipContent = 'Annotation Count:<br/>' + annotCounts + '<br/><a target="_blank" href="' + linkout + '">' + objId + ' - ' + nodeName + '</a>';
            \$('#info').html( qtipContent );
        });

// STILL NEED THIS ON WB ?
//  o fade out nodes on loading and remove buttons
        var nodes = cyPhenGraph.nodes();
        for( var i = 0; i < nodes.length; i++ ){
          var node     = nodes[i];
          var nodeId   = node.data('id');
          if (document.getElementById(nodeId)) { 	// if there's a button for this goslim term, remove faded
            document.getElementById(nodeId).style.display = ''; }
        }
// END STILL NEED THIS ON WB ?

        var parentToChild = new Object();
        var nodes = cyPhenGraph.nodes();
        for( var i = 0; i < nodes.length; i++ ){
           var source = nodes[i].data('id');
           parentToChild[source] = []; }
        var edges = cyPhenGraph.edges();
        for( var i = 0; i < edges.length; i++ ){
           var source = edges[i].data('source');
           var target = edges[i].data('target');
           parentToChild[source].push(target);
//            console.log('s ' + source + ' t ' + target); 
        }

//         recurseChildren(parentToChild, 'GO:0000000');	// just to show stuff
        

        var nodeCount = cyPhenGraph.nodes().length;
        \$('#nodeCount').html('node count: ' + nodeCount + '<br/>');
        var edgeCount = cyPhenGraph.edges().length;
        \$('#edgeCount').html('edge count: ' + edgeCount + '<br/>');
      }

    });
  } // function initCy( then )

// probably for debugging
//   function recurseChildren(parentToChild, obj ){
//     for( var i = 0; i < parentToChild[obj].length; i++ ){
//       var newObj = parentToChild[obj][i];
//       console.log('parent ' + obj + ' child ' + newObj);
//       recurseChildren(parentToChild, newObj);
//     }
//   }


  \$('#radio_weighted').on('click', function(){
console.log('radio_weighted');
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
console.log('radio_unweighted');
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
  var updatingElements = ['radio_etgo_withiea', 'radio_etgo_excludeiea', 'radio_etgo_onlyiea', 'radio_etd_all', 'radio_etd_excludeiea', 'radio_eta_all', 'radio_eta_onlyexprcluster', 'radio_eta_onlyexprpattern',  'radio_etp_all', 'radio_etp_onlyrnai', 'radio_etp_onlyvariation', 'fakeRootFlag', 'filterForLcaFlag', 'filterLongestFlag', 'root_bp', 'root_cc', 'root_mf'];
  updatingElements.forEach(function(element) {
    \$('#'+element).on('click', { name: element },  updateElements); });
  \$('#maxNodes').on('blur', { name: "maxNodes" }, updateElements);
  \$('#maxDepth').on('change', { name: "maxDepth" }, updateElements);
  function updateElements(event) {
console.log( "Updating from " + event.data.name );
    \$('#controldiv').hide(); \$('#loadingdiv').show();		// show loading and hide controls while graph loading
    var radioEtgo = \$('input[name=radio_etgo]:checked').val();
    var radioEtp  = \$('input[name=radio_etp]:checked').val();
    var radioEtd  = \$('input[name=radio_etd]:checked').val();
    var radioEta  = \$('input[name=radio_eta]:checked').val();
// console.log('radioEtp ' + radioEtp + ' end');
    var rootsPossible = ['root_bp', 'root_cc', 'root_mf'];
    var rootsChosen = [];
    var showControlsFlagValue = '0'; if (\$('#showControlsFlag').is(':checked')) { showControlsFlagValue = 1; }
    var fakeRootFlagValue = '0'; if (\$('#fakeRootFlag').is(':checked')) { fakeRootFlagValue = 1; }
    var filterForLcaFlagValue = '0'; if (\$('#filterForLcaFlag').is(':checked')) { filterForLcaFlagValue = 1; }
    var filterLongestFlagValue = '0'; if (\$('#filterLongestFlag').is(':checked')) { filterLongestFlagValue = 1; }
    var maxNodes = 0; if (\$('#maxNodes').val()) { maxNodes = \$('#maxNodes').val(); }
    var maxDepth = 0; 
    if (event.data.name === 'maxDepth') {
      if (\$('#maxDepth').val()) { maxDepth = \$('#maxDepth').val(); } }
    rootsPossible.forEach(function(rootTerm) {
      if (document.getElementById(rootTerm).checked) { rootsChosen.push(document.getElementById(rootTerm).value); } });
    var rootsChosenGroup = rootsChosen.join(',');
    var url = 'soba_biggo.cgi?action=annotSummaryJson&focusTermId=$focusTermId&datatype=$datatype';
    if ( ('$datatype' === 'go') || ('$datatype' === 'biggo') ) { url += '&radio_etgo=' + radioEtgo; }
      else if ('$datatype' === 'phenotype') {                    url += '&radio_etp='  + radioEtp;  }
      else if ('$datatype' === 'disease') {                      url += '&radio_etd='  + radioEtd;  }
      else if ('$datatype' === 'anatomy') {                      url += '&radio_eta='  + radioEta;  }
    url += '&rootsChosen=' + rootsChosenGroup + '&showControlsFlag=' + showControlsFlagValue + '&fakeRootFlag=' + fakeRootFlagValue + '&filterForLcaFlag=' + filterForLcaFlagValue + '&filterLongestFlag=' + filterLongestFlagValue + '&maxNodes=' + maxNodes + '&maxDepth=' + maxDepth;
    var graphPNew = \$.ajax({
      url: url,
      type: 'GET',
      dataType: 'json'
    });
    Promise.all([ graphPNew ]).then(newCy);
    function newCy( then ){
      var elementsNew = then[0].elements;
      \$('#controldiv').show(); \$('#loadingdiv').hide();	// show controls and hide loading when graph loaded
      cyPhenGraph.json( { elements: elementsNew } );
      cyPhenGraph.elements().layout({ name: 'dagre', padding: 10, nodeSep: 5 });
      var nodeCount = cyPhenGraph.nodes().length;
      if (\$('#fakeRootFlag').is(':checked')) { nodeCount--; }
      \$('#nodeCount').html('node count: ' + nodeCount + '<br/>');
      var edgeCount = cyPhenGraph.edges().length;
      \$('#edgeCount').html('edge count: ' + edgeCount + '<br/>');
      var maxOption = then[0].elements.meta.fullDepth;
      var maxDepthElement = document.getElementById('maxDepth');
      var userSelectedValue = maxDepthElement.options[maxDepthElement.selectedIndex].value;
      maxDepthElement.options.length = 0;
      for( var i = 1; i <= maxOption; i++ ){
        var label = i; 
//         if ((i == 0) || (i == maxOption)) { label = 'max'; }
        maxDepthElement.options[i-1] = new Option(label, i, true, false) }
      maxDepthElement.selectedIndex = maxOption - 1;
      if (event.data.name === 'maxDepth') { maxDepthElement.value = userSelectedValue; }
//       if (userSelectedValue <= maxDepthElement.value) { maxDepthElement.value = userSelectedValue; }
    }
  } // function updateElements()


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
  <div id="loadingdiv" style="z-index: 9999; border: 1px solid #aaa; position: relative; float: left; width: 200px; display: '';">Loading <img src="loading.gif" /></div>
  <div id="controldiv" style="z-index: 9999; border: 1px solid #aaa; position: relative; float: left; width: 200px; display: none;">
    <div id="exportdiv" style="z-index: 9999; position: relative; top: 0; left: 0; width: 200px;">
      <button id="view_png_button">export png</button>
      <button id="view_edit_button" style="display: none;">go back</button><br/>
    </div>
    <div id="legenddiv" style="z-index: 9999; position: relative; top: 0; left: 0; width: 200px;">
    <span id="autocompleteValue">$autocompleteValue</span><br/><br/>
    <span id="descriptionTerms">$descriptionTerms</span><br/><br/>
    <span id="nodeCount" style="display: $show_node_count ">node count<br/></span>
    <span id="edgeCount" style="display: $show_node_count ">edge count<br/></span>
    Graph Depth<select size="1" id="maxDepth" name="maxDepth"></select><br/><br/>
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

    <tr><td valign="center"><svg width="22pt" height="22pt" viewBox="0 0 292.64526 63.826207">
    <defs><marker id="marker4922" style="overflow:visible"> <path style="fill:#949494;fill-opacity:1;fill-rule:evenodd;stroke:#5f5f5f;stroke-width:0.625;stroke-linejoin:round;stroke-opacity:1" d="M 8.7185878,4.0337352 -2.2072895,0.01601326 8.7185884,-4.0017078 c -1.7454984,2.3720609 -1.7354408,5.6174519 -6e-7,8.035443 z" transform="matrix(-1.1,0,0,-1.1,-1.1,0)" /> </marker> </defs>
    <g transform="translate(-151.41157,-412.12323)"> <path style="fill:#949494;fill-opacity:1;fill-rule:evenodd;stroke:#5f5f5f;stroke-width:6.69999981;stroke-linecap:butt;stroke-linejoin:miter;stroke-miterlimit:4;stroke-dasharray:none;stroke-opacity:1;marker-end:url(#marker4922)" d="m 151.42857,445.21935 281.42857,-1.42857" /></g>
    </svg></td><td valign="center">Inference Direction</td></tr>

    <!--<tr><td valign="center"><svg width="22pt" height="22pt" viewBox="0.00 0.00 44.00 44.00"> <g class="graph" transform="scale(1 1) rotate(0) translate(4 40)"> <polygon points="-4,4 -4,-40 40,-40 40,4 -4,4" fill="white" /> <g class="node" style="fill:#ff0000;fill-opacity:1" transform="translate(0,-19.2)"> <path d="M 35.99863,-0.58027907 A 18,18 0 0 1 27.088325,15.178899 18,18 0 0 1 8.9846389,15.221349 18,18 0 0 1 5.2625201e-4,-0.49586946" transform="scale(1,-1)" /> </g> <path style="fill:#0000ff;fill-opacity:1;stroke:#0000ff;stroke-width:1;stroke-dasharray:5, 2" d="m 36.07799,-18.703936 a 18,18 0 0 1 -9.000001,15.5884578 18,18 0 0 1 -17.9999999,-4e-7 18,18 0 0 1 -8.99999952,-15.5884574" /> </g> </svg></td><td valign="center">AGR Slim terms</td></tr>-->

    <tr id="trAllianceSlimWithout" style="display: none"><td valign="center"><svg width="22pt" height="22pt" viewBox="0.00 0.00 44.00 44.00"> <g transform="scale(1 1) rotate(0) translate(4 40)"> <polygon points="-4,4 -4,-40 40,-40 40,4 -4,4" fill="white" /><g style="fill:#9494ff;fill-opacity:1"><ellipse style="fill:#9494ff;fill-opacity:1" ry="18" rx="18" cy="-18" cx="18" stroke-dasharray="5,2" stroke="blue" fill="none" /></g></g></svg></td><td valign="center">Alliance Slim Without Direct Annotation</td></tr>

    <tr id="trAllianceSlimWith" style="display: none"><td valign="center"><svg width="22pt" height="22pt" viewBox="0.00 0.00 44.00 44.00"> <g transform="scale(1 1) rotate(0) translate(4 40)"><polygon points="-4,4 -4,-40 40,-40 40,4 -4,4" fill="white" /><g style="fill:#ffaaaa"><ellipse style="fill:#ffaaaa" ry="18" rx="18" cy="-18" cx="18" stroke="red" fill="none" /></g></g></svg></td><td valign="center">Alliance Slim With Direct Annotation</td></tr>

    </table></div>
    <form method="get" action="soba_biggo.cgi">
      <div id="weightstate" style="z-index: 9999; position: relative; top: 0; left: 0; width: 200px;">
        <input type="radio" name="radio_type" id="radio_weighted"   checked="checked" >Annotation weighted</input><br/>
        <input type="radio" name="radio_type" id="radio_unweighted">Annotation unweighted</input><br/>
      </div><br/>
      <div id="evidencetypeanatomy" style="z-index: 9999; position: relative; top: 0; left: 0; width: 200px; display: none;">
        <input type="radio" name="radio_eta"  id="radio_eta_all"             value="radio_eta_all"             $checked_radio_eta_all >all evidence types</input><br/>
        <input type="radio" name="radio_eta"  id="radio_eta_onlyexprcluster" value="radio_eta_onlyexprcluster" $checked_radio_eta_onlyexprcluster >only expression cluster</input><br/>
        <input type="radio" name="radio_eta"  id="radio_eta_onlyexprpattern" value="radio_eta_onlyexprpattern" $checked_radio_eta_onlyexprpattern >only expression pattern</input><br/>
      </div><br/>
      <div id="evidencetypephenotype" style="z-index: 9999; position: relative; top: 0; left: 0; width: 200px; display: none;">
        <input type="radio" name="radio_etp"  id="radio_etp_all"           value="radio_etp_all"           $checked_radio_etp_all >all evidence types</input><br/>
        <input type="radio" name="radio_etp"  id="radio_etp_onlyrnai"      value="radio_etp_onlyrnai"      $checked_radio_etp_onlyrnai >only rnai</input><br/>
        <input type="radio" name="radio_etp"  id="radio_etp_onlyvariation" value="radio_etp_onlyvariation" $checked_radio_etp_onlyvariation >only variation</input><br/>
      </div><br/>
      <div id="evidencetypedisease" style="z-index: 9999; position: relative; top: 0; left: 0; width: 200px; display: none;">
        <input type="radio" name="radio_etd" id="radio_etd_all"        value="radio_etd_all"        $checked_radio_etd_all ><a href="http://geneontology.org/docs/guide-go-evidence-codes/" target="_blank">all evidence types</a></input><br/>
        <input type="radio" name="radio_etd" id="radio_etd_excludeiea" value="radio_etd_excludeiea" $checked_radio_etd_excludeiea >exclude IEA</input><br/>
      </div><br/>
      <div id="evidencetypego" style="z-index: 9999; position: relative; top: 0; left: 0; width: 200px; display: none;">
        <input type="radio" name="radio_etgo" id="radio_etgo_withiea"    value="radio_etgo_withiea"    $checked_radio_etgo_withiea ><a href="http://geneontology.org/docs/guide-go-evidence-codes/" target="_blank">all evidence types</a></input><br/>
        <input type="radio" name="radio_etgo" id="radio_etgo_excludeiea" value="radio_etgo_excludeiea" $checked_radio_etgo_excludeiea >exclude IEA</input><br/>
        <input type="radio" name="radio_etgo" id="radio_etgo_onlyiea"    value="radio_etgo_onlyiea"    $checked_radio_etgo_onlyiea >experimental evidence only</input><br/>
      </div><br/>
      <div id="rootschosen" style="z-index: 9999; position: relative; top: 0; left: 0; width: 200px; display: none;">
        <input type="checkbox" name="root_bp" id="root_bp" value="GO:0008150" $checked_root_bp >Biological Process</input><br/>
        <input type="checkbox" name="root_cc" id="root_cc" value="GO:0005575" $checked_root_cc >Cellular Component</input><br/>
        <input type="checkbox" name="root_mf" id="root_mf" value="GO:0003674" $checked_root_mf >Molecular Function</input><br/>
      </div><br/>
      <input type="hidden" name="focusTermId" value="$focusTermId">
      <div id="controlMenu" style="display: $displayControlMenu;">
        <!--Max Nodes<input type="input" size="3" id="maxNodes" name="maxNodes" value="0"><br/>-->
        <input type="checkbox" id="showControlsFlag"  name="showControlsFlag"  value="1" $checked_showControls>Show Controls<br/>
        <div id="hidethis" style="display: none;"> <input type="checkbox" id="nodeCountFlag"     name="nodeCountFlag"     value="1" $checked_nodeCount>Node Count<br/></div>
        <input type="checkbox" id="fakeRootFlag"      name="fakeRootFlag"      value="1" $checked_fakeRoot>Fake Root<br/>
        <input type="checkbox" id="filterForLcaFlag"  name="filterForLcaFlag"  value="1" $checked_filterLca>Filter LCA Nodes<br/>
        <input type="checkbox" id="filterLongestFlag" name="filterLongestFlag" value="1" $checked_filterLongest>Filter Longest Edges<br/>
        <br/>
      </div>
    </form>
    <div id="info" style="z-index: 9999; position: relative; top: 0; left: 0; width: 200px;">Mouseover or click node for more information.</div><br/>
    <div id="goSlimDiv" style="display: none">$goslimButtons</div><br/>
  </div>
</div>
EndOfText
print qq($return);
print qq($toPrint);
print qq(</body></html>);
} # sub annotSummaryCytoscape

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
  foreach my $annotTerm (@terms) {
    foreach my $child (sort keys %{ $edgesAll{$annotTerm} }) {
      if ($inBoth{$child}) {
        foreach my $parent (sort keys %{ $edgesAll{$annotTerm}{$child} }) { $ancestorNodes{$parent}++; } } } }
  my %lca;
  foreach my $bothNode (sort keys %inBoth) {
    unless ($ancestorNodes{$bothNode}) { $lca{$bothNode}++; }
  }
  return \%lca;
} # sub calculateLCA


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
      my $nodes     = join", ", @$finpath;
      my @finalpath = @$finpath;					# array of nodes connecting a final path
      my $fromLongestPath = 'longest';
      if ($nodeCount eq $max_nodes) { $fromLongestPath = 'longest'; }
         else { $fromLongestPath = 'notlongest'; }
      for my $i (0 .. $nodeCount - 2) {					# get pairs of edges
        my $source = $finalpath[$i]; 
        my $target = $finalpath[$i+1]; 
        $edgesFromFinalPath{$fromLongestPath}{$source}{$target}++;	# sort into hash of edges derived from final paths
      }
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


sub printHtmlFooter { print qq(</body></html>\n); }

sub printHtmlHeader { 
  my $javascript = << "EndOfText";
<script src="http://code.jquery.com/jquery-1.9.1.js"></script>
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

