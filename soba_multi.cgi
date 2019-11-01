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

# let-4 

# WBbt:0006817                0.02
# WBbt:0006814                0.02
# WBbt:0003927                0.02
# WBbt:0006976                0.02
# WBbt:0004096                0.02
# WBbt:0005664                0.02
# WBbt:0003827                0.033
# WBbt:0003826                0.033
# WBbt:0007808                0.033
# WBbt:0007807                0.033
# WBbt:0005668                0.033
# WBbt:0008434            0.033
# WBbt:0008433            0.033
# WBbt:0005661                0.033
# WBbt:0005465        0.036
# WBbt:0005448            0.05
# WBbt:0005835                0.084
# WBbt:0006828                0.087
# 
# 
# GO:0061458    0.07
# GO:0048569    0.07
# GO:0043632    0.072
# GO:0007568    0.072
# GO:0030163    0.099

# test 3 


use CGI;
use strict;
use LWP::Simple;
use LWP::UserAgent;
use JSON;
use Tie::IxHash;                                # allow hashes ordered by item added
use Net::Domain qw(hostname hostfqdn hostdomain);
use URI::Encode qw(uri_encode uri_decode);
use Storable qw(dclone);			# copy hash of hashes
use POSIX;


use Time::HiRes qw( time );
my $startTime = time; my $prevTime = time;
$startTime =~ s/(\....).*$/$1/;
$prevTime  =~ s/(\....).*$/$1/;

my $hostname = hostname();

my ($cshlHeader, $cshlFooter) = &cshlNew();


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

# http://wobr2.caltech.edu/~azurebrd/cgi-bin/soba_biggo.cgi?radio_datatype=phenotype&gene=let-23+%28Caenorhabditis+elegans%2C+WB%3AWBGene00002299%2C+-%2C+ZK1067.1%29&gene=lin-3+%28Caenorhabditis+elegans%2C+WB%3AWBGene00002992%2C+-%2C+F36H1.4%29&action=Graph+Two+Genes

  if ($action eq 'annotSummaryCytoscape')           { &annotSummaryCytoscape('source_gene'); }
    elsif ($action eq 'annotSummaryGraph')          { &annotSummaryGraph();     }
    elsif ($action eq 'annotSummaryJson')           { &annotSummaryJson();      }	# temporarily keep this for the live www.wormbase going through the fake phenotype_graph_json widget
    elsif ($action eq 'annotSummaryJsonp')          { &annotSummaryJsonp();     }	# new jsonp widget to get directly from .wormbase without fake widget
    elsif ($action eq 'frontPage')                  { &frontPage();     }	# autocomplete on gene names
    elsif ($action eq 'Analyze Terms')              { &annotSummaryCytoscape('source_ontology');     }    # autocomplete on gene names
    elsif ($action eq 'autocompleteXHR')            { &autocompleteXHR(); }
    elsif ($action eq 'autocompleteTazendraXHR')    { &autocompleteTazendraXHR(); }
    elsif ($action eq 'One Gene to SObA Graph')     { &pickOneGenePage(); }
    elsif ($action eq 'Gene Pair to SObA Graph')    { &pickTwoGenesPage(); }
    elsif ($action eq 'Terms to SObA Graph')        { &pickOntologyTermsPage(); }
    elsif ($action eq 'Graph Two Genes')            { &annotSummaryCytoscape('source_gene'); }
    elsif ($action eq 'Graph One Gene')             { &annotSummaryCytoscape('source_gene'); }
    else { &frontPage(); }				# no action, show dag by default
} # sub process

sub autocompleteXHR {
  print "Content-type: text/html\n\n";
  my ($var, $words) = &getHtmlVar($query, 'query');
  unless ($words) { ($var, $words) = &getHtmlVar($query, 'query'); }
  ($var, my $field) = &getHtmlVar($query, 'field');
  if ($field eq 'Gene') { &autocompleteGene($words); }
} # sub autocompleteXHR

sub autocompleteTazendraXHR {
  print "Content-type: text/html\n\n";
  my ($var, $words) = &getHtmlVar($query, 'query');
  ($var, my $objectType) = &getHtmlVar($query, 'objectType');
  if ($objectType eq 'gene') { 
    my $url = 'http://tazendra.caltech.edu/~azurebrd/cgi-bin/forms/datatype_objects.cgi?action=autocompleteXHR&objectType=gene&userValue=' . $words;
    my $page_data = get $url;
    if ($page_data) { print qq($page_data\n); } }
} # sub autocompleteTazendraXHR

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
# print qq($solr_gene_url<br><br>\n\n);
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

sub validateListTermsQvalue {
  my ($data) = @_;
  my (@termsQvalue) = split/\n/, $data;
  my %types;
  my %termsQvalue = ();
  my $errorMessage = '';
  foreach my $termQvalue (@termsQvalue) {
    if ($termQvalue =~ m/\s+$/) { $termQvalue =~ s/\s+$//; }
    my ($term, $qvalue) = ('', undef);
    my $orig_qvalue = '';
    if ($termQvalue =~ m/^(\S+)\s+(.*?)$/) {
        ($term, $qvalue) = $termQvalue =~ m/^(\S+)\s+(.*?)$/; 
        if ($qvalue) { $orig_qvalue = $qvalue; }
        if ($qvalue == 0) { $qvalue = 1e-100; $orig_qvalue = "zero"; }			# for a value of zero
      }
      elsif ($termQvalue =~ m/^(\S+)\s+$/) {
        $term = $1; }
      else { 
        $term = $termQvalue; }
    my ($datatype) = &getDatatypeFromObject($term);
    $types{$datatype}++;
    if ($qvalue == undef) {      $qvalue = 0.367879; }			
      elsif ($qvalue < 1e-100) { $qvalue = 1e-100;   }
    $termsQvalue{$term}{qvalue} = $qvalue;
    $termsQvalue{$term}{orig_qvalue} = $orig_qvalue;
  } # foreach my $termQvalue (@termsQvalue)
  my @datatypes = keys %types;
  my $datatype = join", ", @datatypes;
  if ($errorMessage) {
    return (0, $errorMessage, \%termsQvalue);
  } elsif (scalar @datatypes == 1) {
    return (1, $datatype, \%termsQvalue);
  } else {
    return (0, qq(ERROR invalid datatype "$datatype" found.), \%termsQvalue);
  }
} # validateListTermsQvalue

sub getDatatypeFromObject {
  my ($focusTermId) = @_;
  my ($identifierType) = $focusTermId =~ m/^(\w+):/;
  my %idToDatatype;
  $idToDatatype{"WBbt"}        = "anatomy";
  $idToDatatype{"DOID"}        = "disease";
  $idToDatatype{"GO"}          = "go";
  $idToDatatype{"WBls"}        = "lifestage";
  $idToDatatype{"WBPhenotype"} = "phenotype";
  if ($idToDatatype{$identifierType}) { return $idToDatatype{$identifierType}; }
    else { return "$focusTermId"; }
} # sub getSolrUrl


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
#   print "Content-type: text/html\n\n";
#   my $header = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"><HTML><HEAD>';
#   $header .= "<title>$title</title>\n";
#   $header .= "</head>";
#   $header .= '<body class="yui-skin-sam">';
#   print qq($header);
  my $title = 'SObA options page';
  &printHtmlHeader($title);
  print qq(<body class="yui-skin-sam">);
  print qq(<form method="get" action="soba_multi.cgi">);
  print << "EndOfText";
  One Gene to SObA Graph:<br/>
  Enter one gene name to obtain a SObA Graph that illustrates annotations.<br/>
  <input type="submit" name="action" value="One Gene to SObA Graph"><br/><br/><br/>

  Terms to SObA Graph:<br/>
  Enter a list of enriched ontology terms (Anatomy, GO or Phenotype, but not mixed), and associated Q (corrected-P) values to obtain a SObA Graph.<br/>
  <input type="submit" name="action" value="Terms to SObA Graph"><br/><br/><br/>

  Gene Pair to SObA Graph:<br/>
  Enter two gene names to obtain a SObA Graph that illustrates their combined annotations.<br/>
  <input type="submit" name="action" value="Gene Pair to SObA Graph"><br/><br/><br/>
EndOfText

  print qq(</body></html>);
} # sub frontPage

sub pickOntologyTermsPage {
#   print "Content-type: text/html\n\n";
  my $title = 'SObA pick a gene';
#   my $header = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"><HTML><HEAD>';
#   $header .= "<title>$title</title>\n";
#   print qq($header);
  &printHtmlHeader($title);
  print qq(<body class="yui-skin-sam">);
#   my $exampleData = qq(WBbt:0006817     0.00026\nWBbt:0006814   0.00028\nWBbt:0003927   0.00031\nWBbt:0003737   0.00034\nWBbt:0003721   0.00034\nWBbt:0003740   0.00034\nWBbt:0003724   0.00043\nWBbt:0006762   0.00067\nWBbt:0006764   0.0007\nWBbt:0006763    0.00072\n);
  my $exampleData = qq(WBPhenotype:0000012	0.0001\nWBPhenotype:0002056	0.00042\nWBPhenotype:0000462	0.005\nWBPhenotype:0001621	0.049\nWBPhenotype:0000200	0.07\nWBPhenotype:0000033	0.093\n);
  print qq(<form method="post" action="soba_multi.cgi">);
  print qq(<h3>SObA terms - Enter a list of ontology terms (of the same type) and their associated statistical (correct-P or Q) values for a SObA graph</h3>\n);
  print qq(<a href="https://wiki.wormbase.org/index.php/User_Guide/SObA#Pair_of_genes" target="_blank">user guide</a><br/><br/>\n);
  print qq(Enter datatype objects paired with q-values on separate lines:<br/>\n);
  print qq(<textarea rows="8" cols="80" placeholder="$exampleData" name="objectsQvalue" id="objectsQvalue"></textarea>);
  print qq(<input type="hidden" name="filterForLcaFlag" id="filterForLcaFlag" value="1">);
  print qq(<input type="hidden" name="filterLongestFlag" id="filterLongestFlag" value="1">);
  print qq(<input type="hidden" name="showControlsFlag" id="showControlsFlag" value="0">);
  print qq(<input type="submit" name="action" id="analyzePairsButton" value="Analyze Terms"><br/><br/><br/>);
  print qq(</form>);
  print qq(</body></html>);
} # sub pickOntologyTermsPage

sub pickTwoGenesPage {
#   print "Content-type: text/html\n\n";
  my $title = 'SObA pick two genes';
  &printHtmlHeader($title);
  my $header = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"><HTML><HEAD>';
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
    <script type="text/javascript" src="../javascript/soba_multi.js"></script>
EndOfText

#   $header .= "<title>$title</title>\n";
  $header .= "</head>";
  $header .= '<body class="yui-skin-sam">';
  print qq($header);

  print qq(<input type="hidden" name="which_page" id="which_page" value="pickTwoGenesPage">\n);

#   my $datatype = 'biggo';		# by defalt for front page
  my $datatype = 'phenotype';		# by defalt for front page
  my $solr_taxon_url = $base_solr_url . $datatype . '/select?qt=standard&fl=id,taxon,taxon_label&version=2.2&wt=json&rows=0&indent=on&q=*:*&facet=true&facet.field=taxon_label&facet.mincount=1&fq=document_category:%22bioentity%22';
  my $page_data = get $solr_taxon_url;
  my $perl_scalar = $json->decode( $page_data );
  my %jsonHash = %$perl_scalar;

  print qq(<form method="get" action="soba_multi.cgi">\n);
  print qq(<h3>SObA Gene Pair - combines and compares ontology annotations of a pair of genes</h3>\n);
  print qq(<a href="https://wiki.wormbase.org/index.php/User_Guide/SObA#Pair_of_genes" target="_blank">user guide</a><br/><br/>\n);
  print qq(Select an ontology to display.<br/>\n);
# UNDO for biggo
#   my @datatypes = qw( anatomy disease biggo go lifestage phenotype );
  my @datatypes = qw( anatomy disease go lifestage phenotype );
  foreach my $datatype (@datatypes) {
    my $checked = '';
    if ($datatype eq 'phenotype') { $checked = qq(checked="checked"); }
    print qq(<input type="radio" name="radio_datatype" id="radio_datatype" value="$datatype" $checked onclick="setAutocompleteListeners();" >$datatype</input><br/>\n); }
  print qq(<br/>);

  my @fieldCount  = ('One', 'Two');
  my $fieldName = 'geneOneValue';
  foreach my $fieldCount (@fieldCount) {
    my $countGene = 'first'; if ($fieldCount eq 'Two') { $countGene = 'second'; $fieldName = 'autocompleteValue'; }
    print << "EndOfText";
      <B>Choose the $countGene gene <!--<span style="color: red;">*</span>--></B>
      <font size="-2" color="#3B3B3B">Start typing in a gene and choose from the drop-down.</font>
        <span id="containerForcedGene${fieldCount}AutoComplete">
          <div id="forcedGene${fieldCount}AutoComplete">
                <input size="50" name="$fieldName" id="input_Gene${fieldCount}" type="text" style="max-width: 444px; width: 99%; background-color: #E1F1FF;" value="">
                <div id="forcedGene${fieldCount}Container"></div>
          </div></span><br/><br/>
EndOfText
# UNDO for biggo / species selection
    next;
    
    my $div_display = ''; if ($fieldCount eq 'Two') { $div_display = 'style="display: none"'; }
    print qq(<div id="controls$fieldCount" $div_display>\n);
    print qq(<br/>Prioritize search by selecting one or more species.<br/>\n);
    my %taxons;
    
    my @priorityTaxons = ( 'Homo sapiens', 'Arabidopsis thaliana', 'Caenorhabditis elegans', 'Danio rerio', 'Drosophila melanogaster', 'Escherichia coli K-12', 'Mus musculus', 'Rattus norvegicus', 'Saccharomyces cerevisiae S288c' );
    my %priorityTaxons;
    foreach my $taxon (@priorityTaxons) {
      $priorityTaxons{$taxon}++;
      my $taxon_plus = $taxon; $taxon_plus =~ s/ /+/g;
      print qq(<input type="checkbox" class="taxon${fieldCount}" name="${fieldCount}$taxon" id="${fieldCount}$taxon" value="$taxon_plus" onclick="setAutocompleteListeners();">$taxon</input><br/>\n);
    }
    print qq(<br/>);
    print qq(<br/>Additional species.<br/>);
    
    while (scalar (@{ $jsonHash{"facet_counts"}{"facet_fields"}{"taxon_label"} }) > 0) {
      my $taxon      = shift @{ $jsonHash{"facet_counts"}{"facet_fields"}{"taxon_label"} };
      my $someNumber = shift @{ $jsonHash{"facet_counts"}{"facet_fields"}{"taxon_label"} };
      next if ($priorityTaxons{$taxon});	# already entered before
      my $taxon_plus = $taxon; $taxon_plus =~ s/ /+/g;
      $taxons{qq(<input type="checkbox" class="taxon${fieldCount}" name="${fieldCount}$taxon" id="${fieldCount}$taxon" value="$taxon_plus" onclick="setAutocompleteListeners();">$taxon</input><br/>\n)}++;
    }
    foreach my $taxon (sort keys %taxons) {
      print $taxon;
    }
    print qq(</div>\n);
    print qq(<br/><br/>\n);
  }
  print qq(<input type="submit" name="action" value="Graph Two Genes" ></input><br/><br/>\n);
  print qq(<input name="reset" type="reset" value="Reset Gene Inputs" onclick="document.getElementById('input_GeneOne').value=''; document.getElementById('input_GeneTwo').value='';"><br/>\n);
  print qq(</form>\n);

  print qq(</body></html>);
} # sub pickTwoGenesPage

sub pickOneGenePage {
#   print "Content-type: text/html\n\n";
  my $title = 'SObA pick a gene';
  &printHtmlHeader($title);
  my $header = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"><HTML><HEAD>';
  $header .= "<title>$title</title>\n";

#   $header .= '<link rel="stylesheet" href="http://tazendra.caltech.edu/~azurebrd/stylesheets/jex.css" />';
#   $header .= "<link rel=\"stylesheet\" type=\"text/css\" href=\"http://yui.yahooapis.com/2.7.0/build/autocomplete/assets/skins/sam/autocomplete.css\" />";

  $header .= "<style type=\"text/css\">#forcedPersonAutoComplete { width:25em; padding-bottom:2em; } .div-autocomplete { padding-bottom:1.5em; }</style>";
  $header .= qq(<style type="text/css">#forcedProcessAutoComplete { width:30em; padding-bottom:2em; } </style>);

#     <link rel="stylesheet" type="text/css" href="../yui/2.7.0/build/autocomplete/assets/skins/sam/autocomplete.css" />
#     <link rel="stylesheet" type="text/css" href="../stylesheets/jex.css" />
#     <link rel="stylesheet" type="text/css" href="../yui/2.7.0/build/fonts/fonts-min.css" />
#     <script type="text/javascript" src="../yui/2.7.0/build/yahoo-dom-event/yahoo-dom-event.js"></script>
#     <script type="text/javascript" src="../yui/2.7.0/build/connection/connection-min.js"></script>
#     <script type="text/javascript" src="../yui/2.7.0/build/datasource/datasource-min.js"></script>
#     <script type="text/javascript" src="../yui/2.7.0/build/autocomplete/autocomplete-min.js"></script>
#     <script type="text/javascript" src="../javascript/soba_multi.js"></script>
  $header .= <<"EndOfText";
    <link rel="stylesheet" type="text/css" href="http://yui.yahooapis.com/2.7.0/build/autocomplete/assets/skins/sam/autocomplete.css" />
    <link rel="stylesheet" type="text/css" href="http://tazendra.caltech.edu/~azurebrd/stylesheets/jex.css" />
    <link rel="stylesheet" type="text/css" href="http://yui.yahooapis.com/2.7.0/build/fonts/fonts-min.css" />
    <script type="text/javascript" src="http://yui.yahooapis.com/2.7.0/build/yahoo-dom-event/yahoo-dom-event.js"></script>
    <script type="text/javascript" src="http://yui.yahooapis.com/2.7.0/build/connection/connection-min.js"></script>
    <script type="text/javascript" src="http://yui.yahooapis.com/2.7.0/build/datasource/datasource-min.js"></script>
    <script type="text/javascript" src="http://yui.yahooapis.com/2.7.0/build/autocomplete/autocomplete-min.js"></script>
    <script type="text/javascript" src="../javascript/soba_multi.js"></script>
EndOfText

  $header .= "</head>";
  $header .= '<body class="yui-skin-sam">';
  print qq($header);

  print qq(<input type="hidden" name="which_page" id="which_page" value="pickOneGenePage">\n);

#   my $datatype = 'biggo';		# by defalt for front page
  my $datatype = 'phenotype';		# by defalt for front page
  my $solr_taxon_url = $base_solr_url . $datatype . '/select?qt=standard&fl=id,taxon,taxon_label&version=2.2&wt=json&rows=0&indent=on&q=*:*&facet=true&facet.field=taxon_label&facet.mincount=1&fq=document_category:%22bioentity%22';
  my $page_data = get $solr_taxon_url;
  my $perl_scalar = $json->decode( $page_data );
  my %jsonHash = %$perl_scalar;

  print qq(<form method="get" action="soba_multi.cgi">\n);
  print qq(Select a datatype to display.<br/>\n);
# UNDO for biggo
#   my @datatypes = qw( anatomy disease biggo go lifestage phenotype );
  my @datatypes = qw( anatomy disease go lifestage phenotype );
  foreach my $datatype (@datatypes) {
    my $checked = '';
    if ($datatype eq 'phenotype') { $checked = qq(checked="checked"); }
    print qq(<input type="radio" name="radio_datatype" id="radio_datatype" value="$datatype" $checked onclick="setAutocompleteListeners();" >$datatype</input><br/>\n); }
  print qq(<br/>);

  print << "EndOfText";
    <B>Choose a gene <!--<span style="color: red;">*</span>--></B>
    <font size="-2" color="#3B3B3B">Start typing in a gene and choose from the drop-down.</font>
      <span id="containerForcedGeneAutoComplete">
        <div id="forcedGeneAutoComplete">
              <input size="50" name="autocompleteValue" id="input_Gene" type="text" style="max-width: 444px; width: 99%; background-color: #E1F1FF;" value="">
              <div id="forcedGeneContainer"></div>
        </div></span><br/><br/>
EndOfText
  print qq(<input type="submit" name="action" value="Graph One Gene"><br/><br/>\n);
  print qq(<input name="reset" type="reset" value="Reset Gene Input" onclick="document.getElementById('input_Gene').value='';"><br/>\n);

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

  print qq(</form>\n);

  print qq(</body></html>);
} # sub pickOneGenePage


sub calcNodeWidth {
  my ($nodeCount, $maxAnyCount) = @_;
  unless ($nodeCount) { $nodeCount = 1; }				# some values generated from enrichment don't have a count, default to smallest
  unless ($maxAnyCount) { $maxAnyCount = 1; }
  my $nodeWidth    = 1; my $nodeScale = 1.5; my $nodeMinSize = 0.01; 
#   my $logScaler = .6;
  $nodeWidth    = ( sqrt($nodeCount)/sqrt($maxAnyCount) * $nodeScale ) + $nodeMinSize;
# print qq(NC $nodeCount MAC $maxAnyCount NW $nodeWidth E\n);
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
  my ($focusTermId, $geneOneId, $objectsQvalue, $datatype, $rootsChosen, $filterForLcaFlag, $maxDepth, $maxNodes) = @_;
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
  my %nodes;								# node -> 'counts' -> $whichGene/'anygene' -> $evidenceType/'anytype'
                                                                        # node -> qvalue
                                                                        # node -> orig_qvalue
                                                                        # node -> label
                                                                        # node -> annot		annotated node
                                                                        # node -> lca		lca node
  my %edgesPtc;								# edges from parent to child

  my $nodeWidth    = 1;
  my $weightedNodeWidth    = 1;
  my $unweightedNodeWidth  = 1;

  my %annotationNodeidWhichgene = ();					# annotation state 'annot' vs 'any' -> nodeid -> which gene 'geneOne' or 'geneTwo'
  my @annotNodeIds;							# array of annotated terms to loop and do pairwise comparisons

  my %termsQvalue;							# map term to qvalue from user input

# START
  my @geneIds = ();
  if ($focusTermId) {
    push @geneIds, $focusTermId;
    if ($geneOneId) { push @geneIds, $geneOneId; }
    foreach my $geneId (@geneIds) {
      my $whichGene = 'geneOne';
      if ($geneId eq $focusTermId) { $whichGene = 'geneTwo'; }
#     print qq(FT $focusTermId E\n);
      my $annotation_count_solr_url = $solr_url . 'select?qt=standard&indent=on&wt=json&version=2.2&rows=100000&fl=regulates_closure,id,annotation_class&q=document_category:annotation&fq=-qualifier:%22not%22&fq=bioentity:%22' . $geneId . '%22';
      if ($radio_etgo) {
        if ($radio_etgo eq 'radio_etgo_excludeiea') { $annotation_count_solr_url = $solr_url . 'select?qt=standard&indent=on&wt=json&version=2.2&rows=100000&fl=regulates_closure,id,annotation_class&q=document_category:annotation&fq=-qualifier:%22not%22&fq=-evidence_type:IEA&fq=bioentity:%22' . $geneId . '%22'; }
          elsif ($radio_etgo eq 'radio_etgo_onlyiea') { $annotation_count_solr_url = $solr_url . 'select?qt=standard&indent=on&wt=json&version=2.2&rows=100000&fl=bioentity,regulates_closure,id,annotation_class&q=document_category:annotation&fq=-qualifier:%22not%22&fq=evidence_type:(EXP+IDA+IPI+IMP+IGI+IEP)&fq=bioentity:%22' . $geneId . '%22'; } }
      if ($radio_etp) {
        if ($radio_etp eq 'radio_etp_onlyvariation') {  $annotation_count_solr_url = $solr_url . 'select?qt=standard&indent=on&wt=json&version=2.2&rows=100000&fl=regulates_closure,id,annotation_class&q=document_category:annotation&fq=-qualifier:%22not%22&fq=evidence_type:Variation&fq=bioentity:%22' . $geneId . '%22'; }
          elsif ($radio_etp eq 'radio_etp_onlyrnai') {  $annotation_count_solr_url = $solr_url . 'select?qt=standard&indent=on&wt=json&version=2.2&rows=100000&fl=regulates_closure,id,annotation_class&q=document_category:annotation&fq=-qualifier:%22not%22&fq=evidence_type:RNAi&fq=bioentity:%22' . $geneId . '%22'; } }
      if ($radio_etd) {
        if ($radio_etd eq 'radio_etd_excludeiea') { $annotation_count_solr_url = $solr_url . 'select?qt=standard&indent=on&wt=json&version=2.2&rows=100000&fl=regulates_closure,id,annotation_class&q=document_category:annotation&fq=-qualifier:%22not%22&fq=-evidence_type:IEA&fq=bioentity:%22' . $geneId . '%22'; } }
      if ($radio_eta) {
        if ($radio_eta eq 'radio_eta_onlyexprcluster') {       $annotation_count_solr_url = $solr_url . 'select?qt=standard&indent=on&wt=json&version=2.2&rows=100000&fl=regulates_closure,id,annotation_class&q=document_category:annotation&fq=-qualifier:%22not%22&fq=id:(*WB\:WBPaper*)&fq=bioentity:%22' . $geneId . '%22'; }
          elsif ($radio_eta eq 'radio_eta_onlyexprpattern') {  $annotation_count_solr_url = $solr_url . 'select?qt=standard&indent=on&wt=json&version=2.2&rows=100000&fl=regulates_closure,id,annotation_class&q=document_category:annotation&fq=-qualifier:%22not%22&fq=id:(*WB\:Expr*+*WB\:Marker*)&fq=bioentity:%22' . $geneId . '%22'; } }


#     Anatomy, Expr and Expression_cluster (ref.
#     https://wormbase.org/tools/ontology_browser/show_genes?focusTermName=Anatomy&focusTermId=WBbt:0005766).
#     There are three groups of objects WB:Expr***, WBMarker*** (these are Expression patterns), WB:WBPaper*** (these are Expression profiles).

#     amigo.cgi query
#       $annotation_count_solr_url = $solr_url . 'select?qt=standard&indent=on&wt=json&version=2.2&rows=100000&fl=regulates_closure,id,annotation_class&q=document_category:annotation&fq=-qualifier:%22not%22&fq=bioentity:%22WB:' . $geneId . '%22';

      my $page_data   = get $annotation_count_solr_url;                                           # get the URL
#       print qq( annotation_count_solr_url $annotation_count_solr_url\n);                                           # get the URL
#     numFound == 0
      my $perl_scalar = $json->decode( $page_data );                        # get the solr data
      my %jsonHash    = %$perl_scalar;

#       if ($jsonHash{'response'}{'numFound'} == 0) { return ($toReturn, \%nodes, \%nodes); }	# return nothing if there are no annotations found
      next if ($jsonHash{'response'}{'numFound'} == 0);		 	# skip if there are no annotations found, can't return because could have 2 genes

      foreach my $doc (@{ $jsonHash{'response'}{'docs'} }) {
        my $nodeIdAnnotated = $$doc{'annotation_class'};
        $annotationNodeidWhichgene{'annot'}{$nodeIdAnnotated}{$whichGene}++;
        $annotationNodeidWhichgene{'any'}{$nodeIdAnnotated}{$whichGene}++;
        my $id = $$doc{'id'};
        my (@idarray) = split/\t/, $id;
        if ($datatype eq 'anatomy') {  
            my @entries = split/\|/, $idarray[7];
            foreach my $entry (@entries) { 
              my $evidenceType = ''; 
              if ($entry =~ m/^WB:Expr/) {         $evidenceType = 'Expression Pattern'; }
                elsif ($entry =~ m/^WBMarker/) {   $evidenceType = 'Expression Pattern'; }
                elsif ($entry =~ m/^WB:WBPaper/) { $evidenceType = 'Expression Cluster'; }
              if ($evidenceType) {
# FIX ?  nodeIdInferred -> nodeIdAnnotany ?
                foreach my $nodeIdInferred (@{ $$doc{'regulates_closure'} }) {
#       print qq(NODE whichGene $whichGene GOID $nodeIdInferred 1\n);
                  $annotationNodeidWhichgene{'any'}{$nodeIdInferred}{$whichGene}++;	# track which gene inferred nodes came from
#                   $nodes{$nodeIdInferred}{'counts'}{'any'}++;  $nodes{$nodeIdInferred}{'counts'}{$evidenceType}++;  
                  $nodes{$nodeIdInferred}{'counts'}{'anygene'}{'anytype'}++;  $nodes{$nodeIdInferred}{'counts'}{'anygene'}{$evidenceType}++;  
                  $nodes{$nodeIdInferred}{'counts'}{$whichGene}{'anytype'}++;  $nodes{$nodeIdInferred}{'counts'}{$whichGene}{$evidenceType}++; } } } }
          else {
            my $evidenceType = $idarray[6];
            if ($datatype eq 'lifestage') { if ($evidenceType eq 'IDA') { $evidenceType = 'Gene Expression'; } }
            foreach my $nodeIdInferred (@{ $$doc{'regulates_closure'} }) {
#     print qq(NODE whichGene $whichGene GOID $nodeIdInferred 2\n);
              $annotationNodeidWhichgene{'any'}{$nodeIdInferred}{$whichGene}++;		# track which gene inferred nodes came from
#               $nodes{$nodeIdInferred}{'counts'}{'any'}++;  $nodes{$nodeIdInferred}{'counts'}{$evidenceType}++;  
              $nodes{$nodeIdInferred}{'counts'}{'anygene'}{'anytype'}++;  $nodes{$nodeIdInferred}{'counts'}{'anygene'}{$evidenceType}++;  
              $nodes{$nodeIdInferred}{'counts'}{$whichGene}{'anytype'}++;  $nodes{$nodeIdInferred}{'counts'}{$whichGene}{$evidenceType}++; } }
      } # foreach my $doc (@{ $jsonHash{'response'}{'docs'} })
    } # foreach my $geneId (@geneIds)
  } # if ($focusTermId)
    elsif ($objectsQvalue) {
      my ($is_ok, $termsQvalue_datatype, $termsQvalueHref) = &validateListTermsQvalue($objectsQvalue);
      if ($is_ok) {
        my $whichGene = 'geneOne';
        %termsQvalue = %$termsQvalueHref;
        foreach my $term (sort keys %termsQvalue) {
          my $qvalue = $termsQvalue{$term}{qvalue};
          my $orig_qvalue = $termsQvalue{$term}{orig_qvalue};
          $qvalue = $qvalue + 0;			# for some reason this has a linebreak after it, needs to be a number for json
          if ($qvalue == 0) { $qvalue = 0.1; }
          my $scaling = 0;
#           $scaling = 1 / $qvalue;
#           $scaling = -1 * log($qvalue);
          if ($qvalue) {
            $scaling = -1 * log($qvalue); }
          $nodes{$term}{'counts'}{'anygene'}{'anytype'} = $scaling;
          $nodes{$term}{'qvalue'} = $qvalue;
          $nodes{$term}{'orig_qvalue'} = $orig_qvalue;
#           print qq(TERM $term V $termsQvalue{$term}{qvalue} S $scaling E\n);
          $annotationNodeidWhichgene{'annot'}{$term}{$whichGene}++;
          $annotationNodeidWhichgene{'any'}{$term}{$whichGene}++;
        } # foreach my $term (sort keys %termsQvalue)
    }
      else { print qq(Terms did not validate properly. $termsQvalue_datatype<br>\n); }
  }

# END


# amigo.cgi
#     my $annotation_count_solr_url = $solr_url . 'select?qt=standard&indent=on&wt=json&version=2.2&rows=100000&fl=regulates_closure,id,annotation_class&q=document_category:annotation&fq=-qualifier:%22not%22&fq=bioentity:%22WB:' . $focusTermId . '%22';
#     my $phenotype_solr_url = $solr_url . 'select?qt=standard&fl=regulates_transitivity_graph_json,topology_graph_json&version=2.2&wt=json&indent=on&rows=1&fq=-is_obsolete:true&fq=document_category:%22ontology_class%22&q=id:%22' . $phenotypeId . '%22';


  my $errorMessage = '';
  foreach my $nodeIdAnnotated (sort keys %{ $annotationNodeidWhichgene{'annot'} }) {
    push @annotNodeIds, $nodeIdAnnotated;
    my $phenotype_solr_url = $solr_url . 'select?qt=standard&fl=regulates_transitivity_graph_json,topology_graph_json&version=2.2&wt=json&indent=on&rows=1&fq=-is_obsolete:true&fq=document_category:%22ontology_class%22&q=id:%22' . $nodeIdAnnotated . '%22';

    my $page_data   = get $phenotype_solr_url;                                           # get the URL
#     print qq( phenotype_solr_url $phenotype_solr_url\n);
    my $perl_scalar = $json->decode( $page_data );                        # get the solr data
    my %jsonHash    = %$perl_scalar;
    if ($jsonHash{'response'}{'numFound'} == 0) { $errorMessage .= qq($nodeIdAnnotated not found<br/>); }
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
#       my $direction = 'back'; my $style = 'solid';                      # graph arror direction and style
      if ($sub && $obj && $pred) {                                      # if subject + object + predicate
        $edgesAll{$nodeIdAnnotated}{$sub}{$obj}++;				# for an annotated term's edges, each child to its parents
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
# remove this later if it didn't break something to remove it
#       next unless ($transNodes{$id});
# #       $lbl =~ s/ /<br\/>/g;                                                # replace spaces with html linebreaks in graph for more-square boxes
#       my $label = "$lbl";                                          # node label should have full id, not stripped of :, which is required for edge title text
#       if ($nodes{$id}) { 					# if there are annotation counts to variation and/or rnai, add them to the box
#         my $annotCounts = '';
#         foreach my $whichGene (sort keys %{ $nodes{$id}{'counts'} }) {
#           next if ($whichGene eq 'anygene');				# skip 'anygene', only use geneOne / geneTwo
#           $annotCounts .= $whichGene . ' - ';
#           my @annotCounts;
#           foreach my $evidenceType (sort keys %{ $nodes{$id}{'counts'}{$whichGene} }) {
#             next if ($evidenceType eq 'anytype');			# skip 'anytype', only used for relative size to max value
#             push @annotCounts, qq($nodes{$id}{'counts'}{$whichGene}{$evidenceType} $evidenceType); } 
#           $annotCounts .= join"; ", @annotCounts; }
#         $annotCounts .= "\n";
#         $label = qq(LINEBREAK<br\/>$label<br\/><font color="transparent">$annotCounts<\/font>);				# add html line break and annotation counts to the label
#       }
# print qq(ID $id LBL $lbl E\n);
      if ($id && $lbl) { 
        $nodesAll{$nodeIdAnnotated}{$id} = $lbl;
# print qq(nodesAll $nodeIdAnnotated ID $id LBL $lbl E\n);
      }
    }
  } # foreach my $nodeIdAnnotated (sort keys %{ $annotationNodeidWhichgene{'annot'} })

  if (!$filterForLcaFlag) {
     foreach my $annotTerm (sort keys %nodesAll) {
       $nodes{$annotTerm}{annot}++;
       foreach my $nodeIdAny (sort keys %{ $nodesAll{$annotTerm} }) {
#          my $url = "http://www.wormbase.org/species/all/go_term/$nodeIdAny";                              # URL to link to wormbase page for object
           $allLca{$nodeIdAny}++;
           unless ($annotationNodeidWhichgene{'annot'}{$nodeIdAny}) { 					# only add lca nodes that are not annotated terms
# print qq(NODES $nodeIdAny LCA\n);
             $nodes{$nodeIdAny}{lca}++; } } } }
    else {
      while (@annotNodeIds) {
        my $ph1 = shift @annotNodeIds;					# compare each annotated term node to all other annotated term nodes
#         my $url = "http://www.wormbase.org/species/all/go_term/$ph1";                              # URL to link to wormbase page for object
        my $xlabel = $ph1; 	# FIX
        $nodes{$ph1}{annot}++;
        foreach my $ph2 (@annotNodeIds) {				# compare each annotated term node to all other annotated term nodes
          my $lcaHashref = &calculateLCA($ph1, $ph2);
          my %lca = %$lcaHashref;
          foreach my $lca (sort keys %lca) {
#             $url = "http://www.wormbase.org/species/all/go_term/$lca";                              # URL to link to wormbase page for object
            $allLca{$lca}++;
            unless ($annotationNodeidWhichgene{'annot'}{$lca}) { 					# only add lca nodes that are not annotated terms
              $xlabel = $lca; 					# FIX
              $nodes{$lca}{lca}++;
            }
          } # foreach my $lca (sort keys %lca)
        } # foreach my $ph2 (@annotNodeIds)				# compare each annotated term node to all other annotated term nodes
      } # while (@annotNodeIds)
    }

  my %edgesLca;								# edges that exist in graph generated from annoated terms + lca terms + root
  while (@parentNodes) {						# while there are parent nodes, go through them
    my $parent = shift @parentNodes;					# take a parent
    my %edgesPtcCopy = %{ dclone(\%edgesPtc) };				# make a temp copy since edges will be getting deleted per parent
    while (scalar keys %{ $edgesPtcCopy{$parent} } > 0) {		# while parent has children
      foreach my $child (sort keys %{ $edgesPtcCopy{$parent} }) {	# each child of parent
        if ($allLca{$child} || $annotationNodeidWhichgene{'annot'}{$child}) { 			# good node, keep edge when child is an lca or annotated term
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

  return ($toReturn, \%nodes, \%edgesLca, \%annotationNodeidWhichgene, $errorMessage);
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
  my ($var, $geneOneId)         = &getHtmlVar($query, 'geneOneId');
  my ($var, $focusTermName)     = &getHtmlVar($query, 'focusTermName');
  my ($var, $geneOneName)       = &getHtmlVar($query, 'geneOneName');
  my ($var, $datatype)          = &getHtmlVar($query, 'datatype');
  my ($var, $objectsQvalue)     = &getHtmlVar($query, 'objectsQvalue');
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
  my ($return, $nodesHashref, $edgesLcaHashref, $annotationNodeidWhichgeneHashref, $errorMessage) = &calculateNodesAndEdges($focusTermId, $geneOneId, $objectsQvalue, $datatype, $rootsChosen, $filterForLcaFlag, $maxDepth, $maxNodes);
  if ($return) { print qq(RETURN $return ENDRETURN\n); }
  my %nodes    = %$nodesHashref;
# foreach my $node (sort keys %nodes) { print qq(RETURNED NODES $node\n); }
  my %edgesLca = %$edgesLcaHashref;
  my %annotationNodeidWhichgene = ();
  if ($annotationNodeidWhichgeneHashref) { %annotationNodeidWhichgene = %$annotationNodeidWhichgeneHashref; }
  if ($fakeRootFlag) { 
    if ( ($datatype eq 'go') || ($datatype eq 'biggo') ) {
      my $fakeRoot = 'GO:0000000';
      $nodes{$fakeRoot}{label} = 'Gene Ontology';
      $nodesAll{$fakeRoot}{label} = 'Gene Ontology';
      foreach my $sub (@rootsChosen) {
        if ($nodes{$sub}{'counts'}{'anygene'}{'anytype'}) {		# root must have an annotation to be added
          $edgesLca{$fakeRoot}{$sub}++; }				# any existing edge, parent to child 
  } } }

  my @nodes = ();


  my %rootNodes; 
  my %anyRootNodeMaxAnnotationCount;
  foreach my $root (@rootsChosen) { 
     $rootNodes{$root}++; 						# add to roots hash
    foreach my $whichGene (sort keys %{ $nodes{$root}{'counts'} }) {
      if ($nodes{$root}{'counts'}{$whichGene}{'anytype'} > $anyRootNodeMaxAnnotationCount{$whichGene}) { 
        $anyRootNodeMaxAnnotationCount{$whichGene} = $nodes{$root}{'counts'}{$whichGene}{'anytype'}; } } }

  my %rootNodesTotalAnnotationCount;
  my @whichGenes = qw( geneOne geneTwo );
  my $solr_url = $base_solr_url . $datatype . '/';
  foreach my $whichGene (@whichGenes) {
    my $geneId = $geneOneId;
    if ($whichGene eq 'geneTwo') { $geneId = $focusTermId; }
    next unless $geneId;
    if ( ($datatype eq 'go') || ($datatype eq 'biggo') ) {		# go with multi roots has a special query Raymond chose to find total annotations for a gene
        my $total_annotation_count_solr_url = $solr_url . 'select?qt=standard&indent=on&wt=json&version=2.2&rows=100000&fl=regulates_closure,id,annotation_class&q=document_category:annotation&fq=-qualifier:%22not%22&fq=bioentity:%22' . $geneId . '%22';
        my $page_data   = get $total_annotation_count_solr_url;                                           # get the URL
#         print qq( total_annotation_count_solr_url $total_annotation_count_solr_url\n);
        my $perl_scalar = $json->decode( $page_data );                        # get the solr data
        my %jsonHash    = %$perl_scalar;
        if ($jsonHash{'response'}{'numFound'} == 0) { 
            $rootNodesTotalAnnotationCount{$whichGene} = 1;
            $errorMessage .= qq($geneId total annotation count not found<br/>); }
          else {
            $rootNodesTotalAnnotationCount{$whichGene} = $jsonHash{'response'}{'numFound'}; } }
      else {								# datatypes with one root just take the maximum annotations any node has
        $rootNodesTotalAnnotationCount{$whichGene} = $anyRootNodeMaxAnnotationCount{$whichGene}; } }

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

# print qq(RC $rootsChosen RC\n);
# 
# foreach my $node (sort keys %nodes) { print qq(BEFORE NODES $node\n); }

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
# TO FIX
#     @parentNodes = ( "GO:0008150", "GO:0005575", "GO:0003674" );
    
    foreach my $node (@parentNodes) {
#   print qq(NODE $node PN @parentNodes\n);
      foreach my $type (keys %{ $nodes{$node} }) {
        $tempNodes{$node}{$type} = $nodes{$node}{$type}; } }
    if ($maxDepth) {						# if there's a max depth requested
#   print qq(have MAX DEPTH $maxDepth\n);
      if ($nodeDepth == $maxDepth) {				# if requested depth is current depth, save the nodes and edges
#   print qq(NODE DEPTH $nodeDepth == MAX DEPTH $maxDepth\n);
        %lastGoodNodes = %{ dclone(\%tempNodes) };		# doing this here in the case user wants max depth of 1
        %lastGoodEdges = %{ dclone(\%tempEdges) }; } }		# can't stop processing here, need to get fullDepth
    my @nextLayerParentNodes = ();
    while ( (scalar @parentNodes > 0) ) {						# while there are parent nodes, go through them
#   print qq(MAX DEPTH $maxDepth<BR>\n);
#   print qq(NODE DEPTH $nodeDepth<BR>\n);
      my $parent = shift @parentNodes;					# take a parent
#   print qq(PARENT $parent PN @parentNodes\n);
      foreach my $child (sort keys %{ $edgesLca{$parent} }) {		# each child of parent
        $tempEdges{$parent}{$child}++;					# add parent-child edge to final graph
        next if (exists $tempNodes{$child});				# skip children already added through other parent
#         $count++;
#         if ($parent eq 'GO:0000000') { $count--; }			# never count nodes attached to fake root
#   print qq(NODE CHILD $child PARENT $parent\n);
        foreach my $type (keys %{ $nodes{$child} }) {
          $tempNodes{$child}{$type} = $nodes{$child}{$type}; }
        push @nextLayerParentNodes, $child;					# child is a good node, add to parent list to check its children
#   print qq(ADD $child to next layer\n);
      } # foreach my $child (sort keys %{ $edgesLca{$parent} }) 
      if ( (scalar @parentNodes == 0) ) {				# if looked at all parent nodes
#   print qq(DEPTH INCREASE\n);
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
    if ($maxDepth > $fullDepth) {                                       # if a depth higher than full depth is requested, show the whole graph
#   print qq(MaxDepth $maxDepth > fullDepth $fullDepth\n);
      %lastGoodNodes = %{ dclone(\%tempNodes) };
      %lastGoodEdges = %{ dclone(\%tempEdges) }; 
    }
    unless ($maxDepth) {						# if there's no max depth, use the full graph
#   print qq(unless MaxDepth $maxDepth\n);
      %lastGoodNodes = %{ dclone(\%tempNodes) };
      %lastGoodNodes = %{ dclone(\%tempNodes) };
      %lastGoodEdges = %{ dclone(\%tempEdges) }; }
    %nodes = %{ dclone(\%lastGoodNodes) };
    %edgesLca = %{ dclone(\%lastGoodEdges) };
  } # if ($fullDepthFlag)

# foreach my $node (sort keys %nodes) { print qq(STILL NODES $node\n); }


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
    my $annotCounts = '';
    foreach my $whichGene (sort keys %{ $nodes{$node}{'counts'} }) {
      next if ($whichGene eq 'anygene');				# skip 'anygene', only use geneOne / geneTwo
      my $geneName = $geneOneName; my $wbgene = $geneOneId; my $linkcolour = 'red';
      if ($whichGene eq 'geneTwo') { $geneName = $focusTermName; $wbgene = $focusTermId; $linkcolour = 'blue'; }
      $wbgene =~ s/WB://g;
      $annotCounts .= qq(<a href='https://wormbase.org/species/c_elegans/gene/$wbgene' target='_blank' style='color: $linkcolour'>$geneName</a> - Annotation Count: );
      my @annotCounts;
      foreach my $evidenceType (sort keys %{ $nodes{$node}{'counts'}{$whichGene} }) {
        next if ($evidenceType eq 'anytype');			# skip 'anytype', only used for relative size to max value
        push @annotCounts, qq($nodes{$node}{'counts'}{$whichGene}{$evidenceType} $evidenceType); }
      $annotCounts .= join"; ", @annotCounts; 
# to display ratio
#       $annotCounts .= qq( \($nodes{$node}{'counts'}{$whichGene}{'anytype'} / $rootNodesTotalAnnotationCount{$whichGene}\));
      my $annotCountPercentage = int($nodes{$node}{'counts'}{$whichGene}{'anytype'} / $rootNodesTotalAnnotationCount{$whichGene} * 100);
      $annotCounts .= qq( \(${annotCountPercentage}% of total gene annotations\));
      $annotCounts .= "<br/>"; }

    my $diameter = $diameterMultiplier * &calcNodeWidth($nodes{$node}{'counts'}{'anygene'}{'anytype'}, $anyRootNodeMaxAnnotationCount{'anygene'});
# print qq(NODE $node DIAMETER $diameter E\n);
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
# for testing gene one vs gene two by font colour
#     if ($geneOneId) {
#       if ( $annotationNodeidWhichgene{'any'}{$node}{'geneOne'} && $annotationNodeidWhichgene{'any'}{$node}{'geneTwo'} ) { $labelColor = 'purple'; }
#         elsif ( $annotationNodeidWhichgene{'any'}{$node}{'geneOne'} ) { $labelColor = 'red'; }
#         elsif ( $annotationNodeidWhichgene{'any'}{$node}{'geneTwo'} ) { $labelColor = 'blue'; } }
    my $nodeExpandable = 'false'; 
# label nodes green if they have a child it could expand into, not relevant 2019 02 08
#     foreach my $child (sort keys %{ $edgesLca{$node} }) {               # each child of node
# # print qq(NODE $node CHILD $child HAS $nodes{$child}{label} E<br>\n);
#       unless ($nodes{$child}{label}) { 
# # print qq(BLANK NODE $node CHILD $child HAS $nodes{$child}{label} E<br>\n);
#         $labelColor = 'green';
#         $nodeExpandable = 'true'; 
#     } }
    
    my $qvalue = 'not determined';
    if ($nodes{$node}{'orig_qvalue'}) { $qvalue = $nodes{$node}{'orig_qvalue'}; }
#     if ($termsQvalue{$node}) { $qvalue = $termsQvalue{$node}; }
#     $qvalue = '0.0001';
#     my $qvalueEntry = qq("qvalue" : ") . $qvalue . qq(",);
 
    my $annotCountsQvalue = '';
    if ($focusTermId) {
      $annotCountsQvalue = qq("annotCounts" : "$annotCounts", "qvalue" : "undefined");
    } 
    elsif ($objectsQvalue) {
      $annotCountsQvalue = qq("annotCounts" : "undefined", "qvalue" : "$qvalue");
    }


    my $geneOnePieSize                = 0; my $geneOnePieOpacity                = 0.5;  my $geneOnePieColor                = 'red';
    my $geneTwoPieSize                = 0; my $geneTwoPieOpacity                = 0.5;  my $geneTwoPieColor                = 'blue';
    my $geneOnePieSizeTotalcount      = 0; my $geneOnePieOpacityTotalcount      = 0.5;  my $geneOnePieColorTotalcount      = 'red';
    my $geneTwoPieSizeTotalcount      = 0; my $geneTwoPieOpacityTotalcount      = 0.5;  my $geneTwoPieColorTotalcount      = 'blue';
    my $geneOnePieSizePercentage      = 0; my $geneOnePieOpacityPercentage      = 0.5;  my $geneOnePieColorPercentage      = 'red';
    my $geneTwoPieSizePercentage      = 0; my $geneTwoPieOpacityPercentage      = 0.5;  my $geneTwoPieColorPercentage      = 'blue';
    my $geneOneMinusPieSize           = 0; my $geneOneMinusPieOpacity           = 0.3;  my $geneOneMinusPieColor           = 'red';
    my $geneTwoMinusPieSize           = 0; my $geneTwoMinusPieOpacity           = 0.3;  my $geneTwoMinusPieColor           = 'blue';
    my $geneOneMinusPieSizeTotalcount = 0; my $geneOneMinusPieOpacityTotalcount = 0.3;  my $geneOneMinusPieColorTotalcount = 'red';
    my $geneTwoMinusPieSizeTotalcount = 0; my $geneTwoMinusPieOpacityTotalcount = 0.3;  my $geneTwoMinusPieColorTotalcount = 'blue';
    my $geneOneMinusPieSizePercentage = 0; my $geneOneMinusPieOpacityPercentage = 0.3;  my $geneOneMinusPieColorPercentage = 'white';
    my $geneTwoMinusPieSizePercentage = 0; my $geneTwoMinusPieOpacityPercentage = 0.3;  my $geneTwoMinusPieColorPercentage = 'white';
    my $whichGeneHighlight = '';
    if ($geneOneId) {
        # slicing by total count
      $geneOnePieSizeTotalcount   = $nodes{$node}{'counts'}{geneOne}{'anytype'} / $nodes{$node}{'counts'}{'anygene'}{'anytype'} * 100;
      $geneTwoPieSizeTotalcount   = $nodes{$node}{'counts'}{geneTwo}{'anytype'} / $nodes{$node}{'counts'}{'anygene'}{'anytype'} * 100; 
# uncomment to add variable opacity
#       my $opacityMultiplier = 0.3;
#       my $opacityFloor = 0.40;
#       if ($rootNodesTotalAnnotationCount{geneOne}) {
#         $geneOnePieOpacityTotalcount = ($nodes{$node}{'counts'}{geneOne}{'anytype'} / $rootNodesTotalAnnotationCount{geneOne} * $opacityMultiplier) + $opacityFloor; }
#       if ($rootNodesTotalAnnotationCount{geneTwo}) {
#         $geneTwoPieOpacityTotalcount = ($nodes{$node}{'counts'}{geneTwo}{'anytype'} / $rootNodesTotalAnnotationCount{geneTwo} * $opacityMultiplier) + $opacityFloor; }

        # slicing by percentage count
      if ( $annotationNodeidWhichgene{'any'}{$node}{'geneOne'} && $annotationNodeidWhichgene{'any'}{$node}{'geneTwo'} ) { 
          $whichGeneHighlight = 'geneBoth';
#           $geneOneMinusPieColorPercentage = 'yellow'; $geneTwoMinusPieColorPercentage = 'yellow'; 
          $geneOneMinusPieOpacityPercentage = 1.0; $geneTwoMinusPieOpacityPercentage = 1.0; }
        elsif ( $annotationNodeidWhichgene{'any'}{$node}{'geneOne'} ) { 
#           $geneOneMinusPieColorPercentage = 'red'; $geneTwoMinusPieColorPercentage = 'red';
          $whichGeneHighlight = 'geneOne'; }
        elsif ( $annotationNodeidWhichgene{'any'}{$node}{'geneTwo'} ) { 
#           $geneOneMinusPieColorPercentage = 'blue'; $geneTwoMinusPieColorPercentage = 'blue';
          $whichGeneHighlight = 'geneTwo'; }
      if ($rootNodesTotalAnnotationCount{geneOne}) {
#         $geneOnePieSizePercentage      = 10 * ceil($nodes{$node}{'counts'}{geneOne}{'anytype'} / $rootNodesTotalAnnotationCount{geneOne} * 5); 	# 10% chunks
        $geneOnePieSizePercentage      = 50 * $nodes{$node}{'counts'}{geneOne}{'anytype'} / $rootNodesTotalAnnotationCount{geneOne}; }
      if ($rootNodesTotalAnnotationCount{geneTwo}) {
#         $geneTwoPieSizePercentage      = 10 * ceil($nodes{$node}{'counts'}{geneTwo}{'anytype'} / $rootNodesTotalAnnotationCount{geneTwo} * 5); 	# 10% chunks
        $geneTwoPieSizePercentage      = 50 * $nodes{$node}{'counts'}{geneTwo}{'anytype'} / $rootNodesTotalAnnotationCount{geneTwo}; }
      $geneOneMinusPieSizePercentage = 50 - $geneOnePieSizePercentage;
      $geneTwoMinusPieSizePercentage = 50 - $geneTwoPieSizePercentage;

        # initialize values to total count
      $geneOnePieSize         = $geneOnePieSizeTotalcount;
      $geneTwoPieSize         = $geneTwoPieSizeTotalcount;
      $geneOnePieOpacity      = $geneOnePieOpacityTotalcount;
      $geneTwoPieOpacity      = $geneTwoPieOpacityTotalcount;
      $geneOnePieColor        = $geneOnePieColorTotalcount;
      $geneTwoPieColor        = $geneTwoPieColorTotalcount;
      $geneOneMinusPieSize    = $geneOneMinusPieSizeTotalcount;
      $geneTwoMinusPieSize    = $geneTwoMinusPieSizeTotalcount;
      $geneOneMinusPieOpacity = $geneOneMinusPieOpacityTotalcount;
      $geneTwoMinusPieOpacity = $geneTwoMinusPieOpacityTotalcount;
      $geneOneMinusPieColor   = $geneOneMinusPieColorTotalcount;
      $geneTwoMinusPieColor   = $geneTwoMinusPieColorTotalcount;
    } # if ($geneOneId)



#     my $pieInfo = qq(, "geneOnePieSize" : $geneOnePieSize, "geneTwoPieSize" : $geneTwoPieSize, "geneOnePieOpacity" : $geneOnePieOpacity, "geneTwoPieOpacity" : $geneTwoPieOpacity);
#     my $pieInfo = qq(, "geneOnePieSize" : $geneOnePieSize, "geneOnePieOpacity" : $geneOnePieOpacity, "geneOnePieColor" : "$geneOnePieColor", "geneOneMinusPieSize" : $geneOneMinusPieSize, "geneOneMinusPieOpacity" : $geneOneMinusPieOpacity, "geneOneMinusPieColor" : "$geneOneMinusPieColor", "geneTwoPieSize" : $geneTwoPieSize, "geneTwoPieOpacity" : $geneTwoPieOpacity, "geneTwoPieColor" : "$geneTwoPieColor", "geneTwoMinusPieSize" : $geneTwoMinusPieSize, "geneTwoMinusPieOpacity" : $geneTwoMinusPieOpacity, "geneTwoMinusPieColor" : "$geneTwoMinusPieColor");
    my $pieInfo = qq(, );
    $pieInfo .= qq("whichGeneHighlight" : "$whichGeneHighlight", );
    $pieInfo .= qq("geneOnePieSize" : $geneOnePieSize, "geneOnePieOpacity" : $geneOnePieOpacity, "geneOnePieColor" : "$geneOnePieColor", );
    $pieInfo .= qq("geneTwoPieSize" : $geneTwoPieSize, "geneTwoPieOpacity" : $geneTwoPieOpacity, "geneTwoPieColor" : "$geneTwoPieColor", );
    $pieInfo .= qq("geneOnePieSizeTotalcount" : $geneOnePieSizeTotalcount, "geneOnePieOpacityTotalcount" : $geneOnePieOpacityTotalcount, "geneOnePieColorTotalcount" : "$geneOnePieColorTotalcount", );
    $pieInfo .= qq("geneTwoPieSizeTotalcount" : $geneTwoPieSizeTotalcount, "geneTwoPieOpacityTotalcount" : $geneTwoPieOpacityTotalcount, "geneTwoPieColorTotalcount" : "$geneTwoPieColorTotalcount", );
    $pieInfo .= qq("geneOnePieSizePercentage" : $geneOnePieSizePercentage, "geneOnePieOpacityPercentage" : $geneOnePieOpacityPercentage, "geneOnePieColorPercentage" : "$geneOnePieColorPercentage", );
    $pieInfo .= qq("geneOneMinusPieSize" : $geneOneMinusPieSize, "geneOneMinusPieOpacity" : $geneOneMinusPieOpacity, "geneOneMinusPieColor" : "$geneOneMinusPieColor", );
    $pieInfo .= qq("geneTwoMinusPieSize" : $geneTwoMinusPieSize, "geneTwoMinusPieOpacity" : $geneTwoMinusPieOpacity, "geneTwoMinusPieColor" : "$geneTwoMinusPieColor", );
    $pieInfo .= qq("geneTwoPieSizePercentage" : $geneTwoPieSizePercentage, "geneTwoPieOpacityPercentage" : $geneTwoPieOpacityPercentage, "geneTwoPieColorPercentage" : "$geneTwoPieColorPercentage", );
    $pieInfo .= qq("geneOneMinusPieSizeTotalcount" : $geneOneMinusPieSizeTotalcount, "geneOneMinusPieOpacityTotalcount" : $geneOneMinusPieOpacityTotalcount, "geneOneMinusPieColorTotalcount" : "$geneOneMinusPieColorTotalcount", );
    $pieInfo .= qq("geneTwoMinusPieSizeTotalcount" : $geneTwoMinusPieSizeTotalcount, "geneTwoMinusPieOpacityTotalcount" : $geneTwoMinusPieOpacityTotalcount, "geneTwoMinusPieColorTotalcount" : "$geneTwoMinusPieColorTotalcount", );
    $pieInfo .= qq("geneOneMinusPieSizePercentage" : $geneOneMinusPieSizePercentage, "geneOneMinusPieOpacityPercentage" : $geneOneMinusPieOpacityPercentage, "geneOneMinusPieColorPercentage" : "$geneOneMinusPieColorPercentage", );
    $pieInfo .= qq("geneTwoMinusPieSizePercentage" : $geneTwoMinusPieSizePercentage, "geneTwoMinusPieOpacityPercentage" : $geneTwoMinusPieOpacityPercentage, "geneTwoMinusPieColorPercentage" : "$geneTwoMinusPieColorPercentage");

    my $cytId = $node; $cytId =~ s/://;
#     my $nodeColor  = 'blue';  	# to colour code nodes by direct vs inferred
    my $nodeColor  = 'black';  
    if ($rootNodes{$node}) {
        next unless (($nodes{$node}{'counts'}{'anygene'}{'anytype'}) || ($objectsQvalue)); 	# only add a root if it has annotations or is soba by ontology terms, which don't have annoatations
        if ($node eq 'GO:0000000') { $nodeColor  = '#fff'; }
        if ( ($goslimIds{$node}) && !($geneOneId) ) { $backgroundColor = $nodeColor; }
# print qq(ROOT NODE $node\n);
        unless ($geneOneId) { $nodeColor = 'blue'; }					# to colour code nodes by direct vs inferred
#         $node =~ s/GO://; 
        push @nodes, qq({ "data" : { "id" : "$cytId", "objId" : "$node", "name" : "$name", $annotCountsQvalue, "borderStyle" : "dashed", "labelColor" : "$labelColor", "nodeColor" : "$nodeColor", "annotationDirectness" : "inferred", "borderWidthUnweighted" : "$borderWidthRoot_unweighted", "borderWidthWeighted" : "$borderWidthRoot_weighted", "borderWidth" : "$borderWidthRoot", "fontSizeUnweighted" : "$fontSize_unweighted", "fontSizeWeighted" : "$fontSize_weighted", "fontSize" : "$fontSize", "diameter" : $diameter, "diameter_weighted" : $diameter_weighted, "diameter_unweighted" : $diameter_unweighted, "backgroundColor" : "$backgroundColor", "nodeShape" : "rectangle", "nodeExpandable" : "$nodeExpandable" $pieInfo } }); }
      elsif ($nodes{$node}{lca}) {
# print qq(LCA NODE $node\n);
        if ( ($goslimIds{$node}) && !($geneOneId) ) { $backgroundColor = 'blue'; }
        unless ($geneOneId) { $nodeColor = 'blue'; }					# to colour code nodes by direct vs inferred
#         $node =~ s/GO://; 
          push @nodes, qq({ "data" : { "id" : "$cytId", "objId" : "$node", "name" : "$name", $annotCountsQvalue, "borderStyle" : "dashed", "labelColor" : "$labelColor", "nodeColor" : "$nodeColor", "annotationDirectness" : "inferred", "borderWidthUnweighted" : "$borderWidth_unweighted", "borderWidthWeighted" : "$borderWidth_weighted", "borderWidth" : "$borderWidth", "fontSizeUnweighted" : "$fontSize_unweighted", "fontSizeWeighted" : "$fontSize_weighted", "fontSize" : "$fontSize", "diameter" : $diameter, "diameter_weighted" : $diameter_weighted, "diameter_unweighted" : $diameter_unweighted, "backgroundColor" : "$backgroundColor", "nodeShape" : "ellipse", "nodeExpandable" : "$nodeExpandable" $pieInfo } });   }
      elsif ($nodes{$node}{annot}) {
# print qq(ANNOT NODE $node\n);
        if ( ($goslimIds{$node}) && !($geneOneId) ) { $backgroundColor = 'red'; }
        unless ($geneOneId) { $nodeColor = 'red'; }					# to colour code nodes by direct vs inferred
#          $node =~ s/GO://; 
         push @nodes, qq({ "data" : { "id" : "$cytId", "objId" : "$node", "name" : "$name", $annotCountsQvalue, "borderStyle" : "solid", "labelColor" : "$labelColor", "nodeColor" : "$nodeColor", "annotationDirectness" : "direct", "borderWidthUnweighted" : "$borderWidth_unweighted", "borderWidthWeighted" : "$borderWidth_weighted", "borderWidth" : "$borderWidth", "fontSizeUnweighted" : "$fontSize_unweighted", "fontSizeWeighted" : "$fontSize_weighted", "fontSize" : "$fontSize", "diameter" : $diameter, "diameter_weighted" : $diameter_weighted, "diameter_unweighted" : $diameter_unweighted, "backgroundColor" : "$backgroundColor", "nodeShape" : "ellipse", "nodeExpandable" : "$nodeExpandable" $pieInfo } });     } 
      else {
# print qq(OTHER NODE $node\n); 
    }
  }

  unless (scalar @nodes > 0) { 
    if ($fakeRootFlag) { 
      if ( ($datatype eq 'go') || ($datatype eq 'biggo') ) {
        push @nodes, qq({ "data" : { "id" : "GO:0000000", "name" : "Gene Ontology", "annotCounts" : "", "qvalue" : "", "borderStyle" : "dashed", "labelColor" : "#888", "nodeColor" : "#888", "borderWidthUnweighted" : "8", "borderWidthWeighted" : "8", "borderWidth" : "8", "fontSizeUnweighted" : "6", "fontSizeWeighted" : "4", "fontSize" : "4", "diameter" : 0.6, "diameter_weighted" : 0.6, "diameter_unweighted" : 40, "backgroundColor" : "white", "nodeShape" : "rectangle" } }); } } }

  unless (scalar @nodes > 0) { 
    my $pieInfo = qq(, );
    $pieInfo .= qq("whichGeneHighlight" : "geneBoth", );
    $pieInfo .= qq("geneOnePieSize" : 100, "geneOnePieOpacity" : 1, "geneOnePieColor" : "blue", );
    $pieInfo .= qq("geneTwoPieSize" : 0, "geneTwoPieOpacity" : 0, "geneTwoPieColor" : "blue", );
    $pieInfo .= qq("geneOnePieSizeTotalcount" : 100, "geneOnePieOpacityTotalcount" : 1, "geneOnePieColorTotalcount" : "blue", );
    $pieInfo .= qq("geneTwoPieSizeTotalcount" : 0, "geneTwoPieOpacityTotalcount" : 0, "geneTwoPieColorTotalcount" : "blue", );
    $pieInfo .= qq("geneOnePieSizePercentage" : 100, "geneOnePieOpacityPercentage" : 1, "geneOnePieColorPercentage" : "blue", );
    $pieInfo .= qq("geneOneMinusPieSize" : 0, "geneOneMinusPieOpacity" : 0, "geneOneMinusPieColor" : "blue", );
    $pieInfo .= qq("geneTwoMinusPieSize" : 0, "geneTwoMinusPieOpacity" : 0, "geneTwoMinusPieColor" : "blue", );
    $pieInfo .= qq("geneTwoPieSizePercentage" : 0, "geneTwoPieOpacityPercentage" : 0, "geneTwoPieColorPercentage" : "blue", );
    $pieInfo .= qq("geneOneMinusPieSizeTotalcount" : 0, "geneOneMinusPieOpacityTotalcount" : 0, "geneOneMinusPieColorTotalcount" : "blue", );
    $pieInfo .= qq("geneTwoMinusPieSizeTotalcount" : 0, "geneTwoMinusPieOpacityTotalcount" : 0, "geneTwoMinusPieColorTotalcount" : "blue", );
    $pieInfo .= qq("geneOneMinusPieSizePercentage" : 0, "geneOneMinusPieOpacityPercentage" : 0, "geneOneMinusPieColorPercentage" : "blue", );
    $pieInfo .= qq("geneTwoMinusPieSizePercentage" : 0, "geneTwoMinusPieOpacityPercentage" : 0, "geneTwoMinusPieColorPercentage" : "blue");
    push @nodes, qq({ "data" : { "id" : "No Annotations", "name" : "No Annotations", "annotCounts" : "1", "qvalue" : "", "borderStyle" : "dashed", "labelColor" : "#888", "nodeColor" : "#888", "borderWidthUnweighted" : "8", "borderWidthWeighted" : "8", "borderWidth" : "8", "fontSizeUnweighted" : "6", "fontSizeWeighted" : "4", "fontSize" : "4", "diameter" : 0.6, "diameter_weighted" : 0.6, "diameter_unweighted" : 40, "backgroundColor" : "white", "nodeShape" : "rectangle" $pieInfo } }); }

  my $ucfirstDatatype = ucfirst($datatype);
  my $nodes = join",\n", @nodes; 
  print qq({ "elements" : {\n);
  print qq("nodes" : [\n);
  print qq($nodes\n);
  print qq(],\n);
  print qq("edges" : [\n);
  print qq($edges\n);
  print qq(]\n);
  print qq(, "meta" : { "fullDepth" : $fullDepth, "focusTermId" : "$focusTermId", "urlBase" : "https://${hostname}.caltech.edu/~raymond/cgi-bin/soba_biggo.cgi?action=annotSummaryJsonp&focusTermId=${focusTermId}&datatype=${ucfirstDatatype}", "errorMessage" : "$errorMessage" } } }\n);
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
  my ($processType) = @_;
  my ($var, $focusTermId)          = &getHtmlVar($query, 'focusTermId');
  ($var, my $autocompleteValue)    = &getHtmlVar($query, 'autocompleteValue');
  ($var, my $geneOneValue)         = &getHtmlVar($query, 'geneOneValue');
  ($var, my $datatype)             = &getHtmlVar($query, 'datatype');
  ($var, my $radio_datatype)       = &getHtmlVar($query, 'radio_datatype');
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
  ($var, my $objectsQvalue)        = &getHtmlVar($query, 'objectsQvalue');
  unless ($datatype) { $datatype = $radio_datatype; }
  my $encodedObjectsQvalue         = uri_encode($objectsQvalue);
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
my $debugText = '';

  my $legendBlueNodeText = 'Without Direct Annotation';
  my $legendRedNodeText = 'With Direct Annotation';
  my $legendWeightstateWeighted = 'Weighted';
  my $legendWeightstateUnweighted = 'Uniform';
#   my $legendPietypeTotalcount = 'Pie Slice Total counts';
#   my $legendPietypePercentage = 'Pie Slice Percentage';
  my $legendPietypeTotalcount = 'Absolute count slices';
  my $legendPietypePercentage = 'Relative count slices';
  my $legendSkipEvidenceStart = '';
  my $legendSkipEvidenceEnd = '';
  my $analyzePairsText = '';
  my %termsQvalue;
  if ($processType eq 'source_ontology') {
    my ($is_ok, $termsQvalue_datatype, $termsQvalueHref) = &validateListTermsQvalue($objectsQvalue);
    if ($is_ok) {
#         $analyzePairsText .= qq(DATATYPE $termsQvalue_datatype<br>\n);
        %termsQvalue = %$termsQvalueHref;
        $datatype = $termsQvalue_datatype; }
      else { $analyzePairsText .= qq(Terms did not validate properly. $termsQvalue_datatype<br>\n); }
    $legendBlueNodeText = 'Inferred Term';
    $legendRedNodeText = 'Enriched Term';
    $legendWeightstateWeighted = 'Significance weighted';
    $legendWeightstateUnweighted = 'Significance unweighted';
    $legendSkipEvidenceStart = '<!--';
    $legendSkipEvidenceEnd = '-->';
  }


  my @roots;
# $debugText .= "DATATYPE $datatype E<br>\n"; 
  if ( ($datatype eq 'go') || ($datatype eq 'biggo') ) {
# $debugText .= "IN DATATYPE $datatype E<br>\n"; 
         $fakeRootFlag = 0; $filterLongestFlag = 1; $filterForLcaFlag = 1; $maxNodes = 0; $maxDepth = 0;
         push @roots, "GO:0008150"; push @roots, "GO:0005575"; push @roots, "GO:0003674";
         $checked_root_bp = 'checked="checked"'; $checked_root_cc = 'checked="checked"'; $checked_root_mf = 'checked="checked"';
# not sure why was doing this
#      if ($all_roots eq 'all_roots') {
#          $fakeRootFlag = 0; $filterLongestFlag = 1; $filterForLcaFlag = 1; $maxNodes = 0; $maxDepth = 0;
#          push @roots, "GO:0008150"; push @roots, "GO:0005575"; push @roots, "GO:0003674";
#          $checked_root_bp = 'checked="checked"'; $checked_root_cc = 'checked="checked"'; $checked_root_mf = 'checked="checked"'; }
#        else {
#          if ($root_bp) { $checked_root_bp = 'checked="checked"'; push @roots, $root_bp; }
#          if ($root_cc) { $checked_root_cc = 'checked="checked"'; push @roots, $root_cc; }
#          if ($root_mf) { $checked_root_mf = 'checked="checked"'; push @roots, $root_mf; } }
 }
    elsif ($datatype eq 'phenotype') { push @roots, "WBPhenotype:0000886"; }
    elsif ($datatype eq 'anatomy')   { push @roots, "WBbt:0000100";        }
    elsif ($datatype eq 'disease')   { push @roots, "DOID:4";              }
    elsif ($datatype eq 'lifestage') { push @roots, "WBls:0000075";        }
  my $roots = join",", @roots;

#   if ($processType eq 'source_gene') {
  my $geneOneId = '';
#   unless ($focusTermId) { ($focusTermId) = $autocompleteValue =~ m/, (.*?),/; }		# autocomplete format from solr query
#   unless ($geneOneId) {   ($geneOneId)   = $geneOneValue      =~ m/, (.*?),/; }		# autocomplete format from solr query
  unless ($focusTermId) { ($focusTermId) = $autocompleteValue =~ m/\( (.*?) \)/; $focusTermId = 'WB:' . $focusTermId; }		# autocomplete format from tazendra OA query
  unless ($geneOneId) {   ($geneOneId)   = $geneOneValue =~ m/\( (.*?) \)/;      $geneOneId   = 'WB:' . $geneOneId;   }		# autocomplete format from tazendra OA query
#   }

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

  my $withoutDirectLegendNodeColor = 'blue';
  my $withDirectLegendNodeColor    = 'red';
# FIX
#   $focusTermId = 'WB:WBGene00001135';
  my $jsonUrl = 'soba_multi.cgi?action=annotSummaryJson&focusTermId=' . $focusTermId . '&datatype=' . $datatype;
  my $geneOneName = ''; my $focusTermName = '';
  my $legendtitlediv = '';
  my ($infogif) = &getInfoGif();
  if ($processType eq 'source_ontology') {
      $legendtitlediv = qq(<h3>SObA Terms - $datatype <a href="https://wiki.wormbase.org/index.php/User_Guide/SObA#List_of_terms" target="_blank">$infogif</a></h3>\n);
#       $jsonUrl = 'soba_multi.cgi?action=annotSummaryJson&objectsQvalue=' . uri_encode($objectsQvalue) . '&datatype=' . $datatype;
      $jsonUrl = 'soba_multi.cgi?action=annotSummaryJson&objectsQvalue=' . $encodedObjectsQvalue . '&datatype=' . $datatype; }
    elsif ($geneOneId) {
      $legendtitlediv = qq(<h3>SObA Gene Pair - $datatype <a href="https://wiki.wormbase.org/index.php/User_Guide/SObA#Pair_of_genes" target="_blank">$infogif</a></h3>\n);
      $withoutDirectLegendNodeColor = 'black';
      $withDirectLegendNodeColor    = 'black';
      ($focusTermName) = $autocompleteValue =~ m/^(.*) \(/;
      ($geneOneName)   = $geneOneValue      =~ m/^(.*) \(/;
      $jsonUrl = 'soba_multi.cgi?action=annotSummaryJson&geneOneId=' . $geneOneId . '&focusTermId=' . $focusTermId . '&geneOneName=' . $geneOneName . '&focusTermName=' . $focusTermName . '&datatype=' . $datatype; }
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
#   $jsonUrl = 'soba_multi.cgi';                  # for post
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

  my $title = qq(<title>$roots $focusTermId Cytoscape view</title>);
  &printHtmlHeader($title);
# Content-type: text/html\n
# <!DOCTYPE html>
# <html>
# <head>
  print << "EndOfText";
<link href="/~azurebrd/work/cytoscape/style.css" rel="stylesheet" />
<link href="https://cdnjs.cloudflare.com/ajax/libs/qtip2/2.2.0/jquery.qtip.min.css" rel="stylesheet" type="text/css" />
<meta charset=utf-8 />
<meta name="viewport" content="user-scalable=no, initial-scale=1.0, minimum-scale=1.0, maximum-scale=1.0, minimal-ui">
<!--<title>$roots $focusTermId Cytoscape view</title>--><!-- put back if removing wormbase style header -->


<script src="https://code.jquery.com/jquery-2.1.0.min.js"></script>

<script src="/~azurebrd/javascript/cytoscape.min.js"></script>

<script src="/~azurebrd/javascript/dagre.min.js"></script>
<script src="https://cdn.rawgit.com/cytoscape/cytoscape.js-dagre/1.1.2/cytoscape-dagre.js"></script>

<script src="https://cdnjs.cloudflare.com/ajax/libs/qtip2/2.2.0/jquery.qtip.min.js"></script>
<script src="https://cdn.rawgit.com/cytoscape/cytoscape.js-qtip/2.2.5/cytoscape-qtip.js"></script>

<script type="text/javascript">
\$(function(){
  // get exported json from cytoscape desktop via ajax
  var data = { action: "annotSummaryJson", datatype: "$datatype" };
  if ('$processType' === 'source_gene')   {                  data["focusTermId"]       = "$focusTermId"; } 
    else if ('$processType' === 'source_ontology') {         data["objectsQvalue"]     = "$encodedObjectsQvalue"; } 
  if ('$geneOneId' !== '') {                                 data["geneOneId"]         = "$geneOneId"; }
  if (('$datatype' === 'go') || ('$datatype' === 'biggo')) { data["radio_etgo"]        = "$radio_etgo"; data["rootsChosen"] = "$roots"; }
    else if ('$datatype' === 'phenotype') {                  data["radio_etp"]         = "$radio_etp"; }
    else if ('$datatype' === 'disease') {                    data["radio_etd"]         = "$radio_etd"; }
    else if ('$datatype' === 'anatomy') {                    data["radio_eta"]         = "$radio_eta"; }
  if ($showControlsFlag !== 0) {                             data["showControlsFlag"]  = "$showControlsFlag"; }
  if ($fakeRootFlag !== 0) {                                 data["fakeRootFlag"]      = "$fakeRootFlag"; }
  if ($filterForLcaFlag !== 0) {                             data["filterForLcaFlag"]  = "$filterForLcaFlag"; }
  if ($filterLongestFlag !== 0) {                            data["filterLongestFlag"] = "$filterLongestFlag"; }
  if ($maxNodes !== 0) {                                     data["maxNodes"]          = "$maxNodes"; }
  if ($maxDepth !== 0) {                                     data["maxDepth"]          = "$maxDepth"; }
  var graphP = \$.ajax({
    url: '$jsonUrl',
    type: 'GET',
    dataType: 'json'
  });
//     data: data,

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
    if ('$geneOneId' !== '') {
        \$('#whichgenehighlight').show();
        \$('#pietype').show(); }
    if ( ('$datatype' === 'go') || ('$datatype' === 'biggo') ) {
         if ('$geneOneId' === '') {
          \$('#trAllianceSlimWith').show(); 
          \$('#trAllianceSlimWithout').show(); 
          \$('#goSlimDiv').show(); }
        \$('#evidencetypego').show(); 
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
            'pie-size': '90%',
            'pie-1-background-color': 'data(geneOnePieColor)',
            'pie-1-background-size': 'mapData(geneOnePieSize, 0, 100, 0, 100)',
            'pie-1-background-opacity': 'data(geneOnePieOpacity)',
            'pie-2-background-color': 'data(geneOneMinusPieColor)',
            'pie-2-background-size': 'mapData(geneOneMinusPieSize, 0, 100, 0, 100)',
            'pie-2-background-opacity': 'data(geneOneMinusPieOpacity)',
            'pie-4-background-color': 'data(geneTwoPieColor)',
            'pie-4-background-size': 'mapData(geneTwoPieSize, 0, 100, 0, 100)',
            'pie-4-background-opacity': 'data(geneTwoPieOpacity)',
            'pie-3-background-color': 'data(geneTwoMinusPieColor)',
            'pie-3-background-size': 'mapData(geneTwoMinusPieSize, 0, 100, 0, 100)',
            'pie-3-background-opacity': 'data(geneTwoMinusPieOpacity)',
            'border-color': 'data(nodeColor)',
            'border-style': 'data(borderStyle)',
            'border-width': 'data(borderWidth)',
            'width': 'data(diameter)',
            'height': 'data(diameter)',
            'text-valign': 'center',
            'text-wrap': 'wrap',
//             'min-zoomed-font-size': 8,		// FIX PUT THIS BACK
//             'border-opacity': 0.3,
            'border-opacity': 0.5,
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

        var errorMessage = then[0].elements.meta.errorMessage;
        document.getElementById('jsonReturnErrorMessage').innerHTML = errorMessage;

//         var maxOption = 7;
        var maxOption = then[0].elements.meta.fullDepth;
        document.getElementById('maxDepth').options.length = 0;
        for( var i = 1; i <= maxOption; i++ ){
          var label = i; 
//           if ((i == 0) || (i == maxOption)) { label = 'max'; }
          document.getElementById('maxDepth').options[i-1] = new Option(label, i, true, false) }
        document.getElementById('maxDepth').selectedIndex = maxOption - 1;

        cyPhenGraph.on('click', 'edge', function(e){
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
          var qvalue = node.data('qvalue');
          var linkout = linkFromNode(objId);
          var qtipContent = '';
//           if (annotCounts !== 'undefined') { qtipContent += 'Annotation Count:' + annotCounts + '<br/>'; }
          if (annotCounts !== 'undefined') { qtipContent += annotCounts + '<br/>'; }
          if (qvalue !== 'undefined') {      qtipContent += 'Q Value: ' + qvalue + '<br/>';          }
          qtipContent += '<a target="_blank" href="' + linkout + '">' + objId + ' - ' + nodeName + '</a>';
//           var qtipContent = 'Annotation Count:<br/>' + annotCounts + '<br/>Q Value :<br/>' + qvalue + '<br/><a target="_blank" href="' + linkout + '">' + objId + ' - ' + nodeName + '</a>';
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
            var qvalue = node.data('qvalue');
            var linkout = linkFromNode(objId);
//             var qtipContent = 'Annotation Count:<br/>' + annotCounts + '<br/>Q Value:<br/>' + qvalue + '<br/><a target="_blank" href="' + linkout + '">' + objId + ' - ' + nodeName + '</a>';
            var qtipContent = '';
//             if (annotCounts !== 'undefined') { qtipContent += 'Annotation Count:' + annotCounts + '<br/>'; }
            if (annotCounts !== 'undefined') { qtipContent += annotCounts + '<br/>'; }
            if (qvalue !== 'undefined') {      qtipContent += 'Q Value: ' + qvalue + '<br/>';          }
            qtipContent += '<a target="_blank" href="' + linkout + '">' + objId + ' - ' + nodeName + '</a>';
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

//             'pie-1-background-color': 'data(geneOnePieColor)',
//             'pie-1-background-size': 'mapData(geneOnePieSize, 0, 100, 0, 100)',
//             'pie-1-background-opacity': 'data(geneOnePieOpacity)',
//             'pie-2-background-color': 'data(geneOneMinusPieColor)',
//             'pie-2-background-size': 'mapData(geneOneMinusPieSize, 0, 100, 0, 100)',
//             'pie-2-background-opacity': 'data(geneOneMinusPieOpacity)',
//             'pie-4-background-color': 'data(geneTwoPieColor)',
//             'pie-4-background-size': 'mapData(geneTwoPieSize, 0, 100, 0, 100)',
//             'pie-4-background-opacity': 'data(geneTwoPieOpacity)',
//             'pie-3-background-color': 'data(geneTwoMinusPieColor)',
//             'pie-3-background-size': 'mapData(geneTwoMinusPieSize, 0, 100, 0, 100)',
//             'pie-3-background-opacity': 'data(geneTwoMinusPieOpacity)',
//             'border-color': 'data(nodeColor)',
//             'border-style': 'data(borderStyle)',
//             'border-width': 'data(borderWidth)',
//             'width': 'data(diameter)',
//             'height': 'data(diameter)',

  \$('#radio_whichgenehighlight_all').on('click', function(){
    cyPhenGraph.elements().removeClass('faded');
  });

  \$('#radio_whichgenehighlight_geneOne').on('click', function(){
console.log('radio_whichgenehighlight_geneOne');
    cyPhenGraph.elements().removeClass('faded');
    var nodes = cyPhenGraph.nodes();
    for( var i = 0; i < nodes.length; i++ ){
      var node     = nodes[i];
      if (node.data('whichGeneHighlight') !== 'geneOne') { node.addClass('faded'); }
    }
  });

  \$('#radio_whichgenehighlight_geneTwo').on('click', function(){
console.log('radio_whichgenehighlight_geneTwo');
    cyPhenGraph.elements().removeClass('faded');
    var nodes = cyPhenGraph.nodes();
    for( var i = 0; i < nodes.length; i++ ){
      var node     = nodes[i];
      if (node.data('whichGeneHighlight') !== 'geneTwo') { node.addClass('faded'); }
    }
  });

  \$('#radio_whichgenehighlight_geneBoth').on('click', function(){
console.log('radio_whichgenehighlight_geneBoth');
    cyPhenGraph.elements().removeClass('faded');
    var nodes = cyPhenGraph.nodes();
    for( var i = 0; i < nodes.length; i++ ){
      var node     = nodes[i];
      if (node.data('whichGeneHighlight') !== 'geneBoth') { node.addClass('faded'); }
    }
  });

  \$('#radio_pietype_percentage').on('click', function(){
console.log('radio_pietype_percentage');
    var nodes = cyPhenGraph.nodes();
    for( var i = 0; i < nodes.length; i++ ){
      var node     = nodes[i];
      var nodeId   = node.data('id');
      var geneOnePieSizePercentage   = node.data('geneOnePieSizePercentage');
      cyPhenGraph.\$('#' + nodeId).data('geneOnePieSize', geneOnePieSizePercentage);
      var geneTwoPieSizePercentage   = node.data('geneTwoPieSizePercentage');
      cyPhenGraph.\$('#' + nodeId).data('geneTwoPieSize', geneTwoPieSizePercentage);
      var geneOneMinusPieSizePercentage = node.data('geneOneMinusPieSizePercentage');
      cyPhenGraph.\$('#' + nodeId).data('geneOneMinusPieSize', geneOneMinusPieSizePercentage);
      var geneTwoMinusPieSizePercentage = node.data('geneTwoMinusPieSizePercentage');
      cyPhenGraph.\$('#' + nodeId).data('geneTwoMinusPieSize', geneTwoMinusPieSizePercentage);
      var geneOnePieColorPercentage   = node.data('geneOnePieColorPercentage');
      cyPhenGraph.\$('#' + nodeId).data('geneOnePieColor', geneOnePieColorPercentage);
      var geneTwoPieColorPercentage   = node.data('geneTwoPieColorPercentage');
      cyPhenGraph.\$('#' + nodeId).data('geneTwoPieColor', geneTwoPieColorPercentage);
      var geneOneMinusPieColorPercentage = node.data('geneOneMinusPieColorPercentage');
      cyPhenGraph.\$('#' + nodeId).data('geneOneMinusPieColor', geneOneMinusPieColorPercentage);
      var geneTwoMinusPieColorPercentage = node.data('geneTwoMinusPieColorPercentage');
      cyPhenGraph.\$('#' + nodeId).data('geneTwoMinusPieColor', geneTwoMinusPieColorPercentage);
      var geneOnePieOpacityPercentage   = node.data('geneOnePieOpacityPercentage');
      cyPhenGraph.\$('#' + nodeId).data('geneOnePieOpacity', geneOnePieOpacityPercentage);
      var geneTwoPieOpacityPercentage   = node.data('geneTwoPieOpacityPercentage');
      cyPhenGraph.\$('#' + nodeId).data('geneTwoPieOpacity', geneTwoPieOpacityPercentage);
      var geneOneMinusPieOpacityPercentage = node.data('geneOneMinusPieOpacityPercentage');
      cyPhenGraph.\$('#' + nodeId).data('geneOneMinusPieOpacity', geneOneMinusPieOpacityPercentage);
      var geneTwoMinusPieOpacityPercentage = node.data('geneTwoMinusPieOpacityPercentage');
      cyPhenGraph.\$('#' + nodeId).data('geneTwoMinusPieOpacity', geneTwoMinusPieOpacityPercentage);
    }
    cyPhenGraph.layout();
  });

  \$('#radio_pietype_totalcount').on('click', function(){
console.log('radio_pietype_totalcount');
    var nodes = cyPhenGraph.nodes();
    for( var i = 0; i < nodes.length; i++ ){
      var node     = nodes[i];
      var nodeId   = node.data('id');
      var geneOnePieSizeTotalcount   = node.data('geneOnePieSizeTotalcount');
      cyPhenGraph.\$('#' + nodeId).data('geneOnePieSize', geneOnePieSizeTotalcount);
      var geneTwoPieSizeTotalcount   = node.data('geneTwoPieSizeTotalcount');
      cyPhenGraph.\$('#' + nodeId).data('geneTwoPieSize', geneTwoPieSizeTotalcount);
      var geneOneMinusPieSizeTotalcount = node.data('geneOneMinusPieSizeTotalcount');
      cyPhenGraph.\$('#' + nodeId).data('geneOneMinusPieSize', geneOneMinusPieSizeTotalcount);
      var geneTwoMinusPieSizeTotalcount = node.data('geneTwoMinusPieSizeTotalcount');
      cyPhenGraph.\$('#' + nodeId).data('geneTwoMinusPieSize', geneTwoMinusPieSizeTotalcount);
      var geneOnePieColorTotalcount   = node.data('geneOnePieColorTotalcount');
      cyPhenGraph.\$('#' + nodeId).data('geneOnePieColor', geneOnePieColorTotalcount);
      var geneTwoPieColorTotalcount   = node.data('geneTwoPieColorTotalcount');
      cyPhenGraph.\$('#' + nodeId).data('geneTwoPieColor', geneTwoPieColorTotalcount);
      var geneOneMinusPieColorTotalcount = node.data('geneOneMinusPieColorTotalcount');
      cyPhenGraph.\$('#' + nodeId).data('geneOneMinusPieColor', geneOneMinusPieColorTotalcount);
      var geneTwoMinusPieColorTotalcount = node.data('geneTwoMinusPieColorTotalcount');
      cyPhenGraph.\$('#' + nodeId).data('geneTwoMinusPieColor', geneTwoMinusPieColorTotalcount);
      var geneOnePieOpacityTotalcount   = node.data('geneOnePieOpacityTotalcount');
      cyPhenGraph.\$('#' + nodeId).data('geneOnePieOpacity', geneOnePieOpacityTotalcount);
      var geneTwoPieOpacityTotalcount   = node.data('geneTwoPieOpacityTotalcount');
      cyPhenGraph.\$('#' + nodeId).data('geneTwoPieOpacity', geneTwoPieOpacityTotalcount);
      var geneOneMinusPieOpacityTotalcount = node.data('geneOneMinusPieOpacityTotalcount');
      cyPhenGraph.\$('#' + nodeId).data('geneOneMinusPieOpacity', geneOneMinusPieOpacityTotalcount);
      var geneTwoMinusPieOpacityTotalcount = node.data('geneTwoMinusPieOpacityTotalcount');
      cyPhenGraph.\$('#' + nodeId).data('geneTwoMinusPieOpacity', geneTwoMinusPieOpacityTotalcount);
    }
    cyPhenGraph.layout();
  });

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
    var jsonUrl = 'soba_multi.cgi?action=annotSummaryJson&focusTermId=$focusTermId&focusTermName=$focusTermName&datatype=$datatype';
    if ('$processType' === 'source_ontology') {
        jsonUrl = 'soba_multi.cgi?action=annotSummaryJson&objectsQvalue=$encodedObjectsQvalue&datatype=$datatype'; }
      else if ('$geneOneId' !== '') {
        jsonUrl = 'soba_multi.cgi?action=annotSummaryJson&geneOneId=$geneOneId&focusTermId=$focusTermId&geneOneName=$geneOneName&focusTermName=$focusTermName&datatype=$datatype'; }
    if ( ('$datatype' === 'go') || ('$datatype' === 'biggo') ) { jsonUrl += '&radio_etgo=' + radioEtgo; }
      else if ('$datatype' === 'phenotype') {                    jsonUrl += '&radio_etp='  + radioEtp;  }
      else if ('$datatype' === 'disease') {                      jsonUrl += '&radio_etd='  + radioEtd;  }
      else if ('$datatype' === 'anatomy') {                      jsonUrl += '&radio_eta='  + radioEta;  }
    jsonUrl += '&rootsChosen=' + rootsChosenGroup + '&showControlsFlag=' + showControlsFlagValue + '&fakeRootFlag=' + fakeRootFlagValue + '&filterForLcaFlag=' + filterForLcaFlagValue + '&filterLongestFlag=' + filterLongestFlagValue + '&maxNodes=' + maxNodes + '&maxDepth=' + maxDepth;
//     jsonUrl = 'soba_multi.cgi';                     // for post
console.log('jsonUrl ' + jsonUrl);
//     var data = { action: "annotSummaryJson", focusTermId: "$focusTermId", datatype: "$datatype" };
    var data = { action: "annotSummaryJson", datatype: "$datatype" };
    if ('$processType' === 'source_gene')   {                  data["focusTermId"]       = "$focusTermId"; } 
      else if ('$processType' === 'source_ontology') {         data["objectsQvalue"]     = "$encodedObjectsQvalue"; } 
    if ('$geneOneId' !== '') {                                 data["geneOneId"]         = "$geneOneId"; }
    if (('$datatype' === 'go') || ('$datatype' === 'biggo')) { data["radio_etgo"] = radioEtgo; data["rootsChosen"] = rootsChosenGroup; }
      else if ('$datatype' === 'phenotype') { data["radio_etp"]         = radioEtp; }
      else if ('$datatype' === 'disease') {   data["radio_etd"]         = radioEtd; }
      else if ('$datatype' === 'anatomy') {   data["radio_eta"]         = radioEta; }
    if (showControlsFlagValue !== 0) {        data["showControlsFlag"]  = showControlsFlagValue; }
    if (fakeRootFlagValue !== 0) {            data["fakeRootFlag"]      = fakeRootFlagValue; }
    if (filterForLcaFlagValue !== 0) {        data["filterForLcaFlag"]  = filterForLcaFlagValue; }
    if (filterLongestFlagValue !== 0) {       data["filterLongestFlag"] = filterLongestFlagValue; }
    if (maxNodes !== 0) {                     data["maxNodes"]          = maxNodes; }
    if (maxDepth !== 0) {                     data["maxDepth"]          = maxDepth; }
    var graphPNew = \$.ajax({
      url: jsonUrl,
      type: 'GET',
      dataType: 'json'
    });
//       data: data,
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
//       document.getElementById("radio_whichgenehighlight_all").checked = true;
      document.getElementById("radio_pietype_totalcount").checked = true;	// when json loads new values, the graph changes to default options for pietype and weighted, so change radio as well
      document.getElementById("radio_weighted").checked = true;
    }
  } // function updateElements()


});
</script>

$debugText

$analyzePairsText

<!--JSONURL $jsonUrl-->

</head>
<body>
<div id="jsonReturnErrorMessage"></div>
<div style="width: 1255px;">
  <div id="cyPhenGraph"  style="border: 1px solid #aaa; float: left;  position: relative; height: 1050px; width: 1050px;"></div>
  <div id="exportdiv" style="width: 1050px; height: 1050px; position: relative; float: left; display: none;"><img id="png-export" style="border: 1px solid #ddd; display: none; max-width: 1050px; max-height: 1050px"></div>
    <div id="loading">
      <span class="fa fa-refresh fa-spin"></span>
    </div>
  <div id="loadingdiv" style="z-index: 9999; border: 1px solid #aaa; position: relative; float: left; width: 200px; display: '';">Loading <img src="loading.gif" /></div>
  <div id="controldiv" style="z-index: 9999; border: 1px solid #aaa; position: relative; float: left; width: 200px; display: none;">
    <div id="legendtitlediv">$legendtitlediv</div>
    <div id="exportdiv" style="z-index: 9999; position: relative; top: 0; left: 0; width: 200px;">
      <button id="view_png_button">Save Image</button>
      <button id="view_edit_button" style="display: none;">go back</button><br/>
    </div>
    <div id="legenddiv" style="z-index: 9999; position: relative; top: 0; left: 0; width: 200px;">
    <span style='color: red'  id="geneOneValue">$geneOneValue</span><br/><br/>
    <span style='color: blue' id="autocompleteValue">$autocompleteValue</span><br/><br/>
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
    <polygon fill="none" stroke="$withoutDirectLegendNodeColor" stroke-dasharray="5,2" points="36,-36 0,-36 0,-0 36,-0 36,-36"/></g></g></svg></td><td valign="center">Root</td></tr>

    <tr><td valign="center"><svg width="22pt" height="22pt" viewBox="0.00 0.00 44.00 44.00" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
    <g id="graph0" class="graph" transform="scale(1 1) rotate(0) translate(4 40)">
    <polygon fill="white" stroke="none" points="-4,4 -4,-40 40,-40 40,4 -4,4"/>
    <g id="node1" class="node"><title></title>
    <ellipse fill="none" stroke="$withoutDirectLegendNodeColor" stroke-dasharray="5,2" cx="18" cy="-18" rx="18" ry="18"/></g></g></svg></td><td valign="center">$legendBlueNodeText</td></tr>

    <tr><td valign="center"><svg width="22pt" height="22pt" viewBox="0.00 0.00 44.00 44.00" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
    <g id="graph0" class="graph" transform="scale(1 1) rotate(0) translate(4 40)">
    <polygon fill="white" stroke="none" points="-4,4 -4,-40 40,-40 40,4 -4,4"/>
    <g id="node1" class="node"><title></title>
    <ellipse fill="none" stroke="$withDirectLegendNodeColor" cx="18" cy="-18" rx="18" ry="18"/></g></g></svg></td><td valign="center">$legendRedNodeText</td></tr>

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
        <input type="radio" name="radio_type" id="radio_weighted"   checked="checked" >$legendWeightstateWeighted</input><br/>
        <input type="radio" name="radio_type" id="radio_unweighted">$legendWeightstateUnweighted</input><br/><br/>
      </div>
      <div id="pietype" style="z-index: 9999; position: relative; top: 0; left: 0; width: 200px; display:none;">
        <input type="radio" name="radio_pietype" id="radio_pietype_totalcount"   checked="checked" >$legendPietypeTotalcount</input><br/>
        <input type="radio" name="radio_pietype" id="radio_pietype_percentage">$legendPietypePercentage</input><br/><br/>
      </div>
      <div id="whichgenehighlight" style="z-index: 9999; position: relative; top: 0; left: 0; width: 200px; display:none;">
        <!--Highlight gene nodes :<br/>-->
        <input type="radio" name="radio_whichgenehighlight" id="radio_whichgenehighlight_all"   checked="checked" >All nodes</input><br/>
        <!--<input type="radio" name="radio_whichgenehighlight" id="radio_whichgenehighlight_geneOne"><a href='https://wormbase.org/species/c_elegans/gene/$geneOneId' target='_blank' style='color: red'>$geneOneName</a></input><br/>
        <input type="radio" name="radio_whichgenehighlight" id="radio_whichgenehighlight_geneTwo"><a href='https://wormbase.org/species/c_elegans/gene/$focusTermId' target='_blank' style='color: blue'>$focusTermName</a></input><br/>-->
        <input type="radio" name="radio_whichgenehighlight" id="radio_whichgenehighlight_geneOne"><span style='color: red'>$geneOneName specific</span></input><br/>
        <input type="radio" name="radio_whichgenehighlight" id="radio_whichgenehighlight_geneTwo"><span style='color: blue'>$focusTermName specific</span></input><br/>
        <input type="radio" name="radio_whichgenehighlight" id="radio_whichgenehighlight_geneBoth">shared</input><br/><br/>
      </div>
      $legendSkipEvidenceStart
      <div id="evidencetypeanatomy" style="z-index: 9999; position: relative; top: 0; left: 0; width: 200px; display: none;">
        <input type="radio" name="radio_eta"  id="radio_eta_all"             value="radio_eta_all"             $checked_radio_eta_all >all evidence types</input><br/>
        <input type="radio" name="radio_eta"  id="radio_eta_onlyexprcluster" value="radio_eta_onlyexprcluster" $checked_radio_eta_onlyexprcluster >only expression cluster</input><br/>
        <input type="radio" name="radio_eta"  id="radio_eta_onlyexprpattern" value="radio_eta_onlyexprpattern" $checked_radio_eta_onlyexprpattern >only expression pattern</input><br/><br/>
      </div>
      <div id="evidencetypephenotype" style="z-index: 9999; position: relative; top: 0; left: 0; width: 200px; display: none;">
        <input type="radio" name="radio_etp"  id="radio_etp_all"           value="radio_etp_all"           $checked_radio_etp_all >all evidence types</input><br/>
        <input type="radio" name="radio_etp"  id="radio_etp_onlyrnai"      value="radio_etp_onlyrnai"      $checked_radio_etp_onlyrnai >only rnai</input><br/>
        <input type="radio" name="radio_etp"  id="radio_etp_onlyvariation" value="radio_etp_onlyvariation" $checked_radio_etp_onlyvariation >only variation</input><br/><br/>
      </div>
      <div id="evidencetypedisease" style="z-index: 9999; position: relative; top: 0; left: 0; width: 200px; display: none;">
        <input type="radio" name="radio_etd" id="radio_etd_all"        value="radio_etd_all"        $checked_radio_etd_all ><a href="http://geneontology.org/docs/guide-go-evidence-codes/" target="_blank">all evidence types</a></input><br/>
        <input type="radio" name="radio_etd" id="radio_etd_excludeiea" value="radio_etd_excludeiea" $checked_radio_etd_excludeiea >exclude IEA</input><br/><br/>
      </div>
      <div id="evidencetypego" style="z-index: 9999; position: relative; top: 0; left: 0; width: 200px; display: none;">
        <input type="radio" name="radio_etgo" id="radio_etgo_withiea"    value="radio_etgo_withiea"    $checked_radio_etgo_withiea ><a href="http://geneontology.org/docs/guide-go-evidence-codes/" target="_blank">all evidence types</a></input><br/>
        <input type="radio" name="radio_etgo" id="radio_etgo_excludeiea" value="radio_etgo_excludeiea" $checked_radio_etgo_excludeiea >exclude IEA</input><br/>
        <input type="radio" name="radio_etgo" id="radio_etgo_onlyiea"    value="radio_etgo_onlyiea"    $checked_radio_etgo_onlyiea >experimental evidence only</input><br/><br/>
      </div>
      $legendSkipEvidenceEnd
      <div id="rootschosen" style="z-index: 9999; position: relative; top: 0; left: 0; width: 200px; display: none;">
        <input type="checkbox" name="root_bp" id="root_bp" value="GO:0008150" $checked_root_bp >Biological Process</input><br/>
        <input type="checkbox" name="root_cc" id="root_cc" value="GO:0005575" $checked_root_cc >Cellular Component</input><br/>
        <input type="checkbox" name="root_mf" id="root_mf" value="GO:0003674" $checked_root_mf >Molecular Function</input><br/><br/>
      </div>
      <input type="hidden" name="focusTermId" value="$focusTermId">	<!-- not sure what this is for -->
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
    foreach my $nodeIdAny (sort keys %{ $nodesAll{$annotTerm} }) {
      $amountInBoth{$nodeIdAny}++; } }
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

# sub printHtmlHeader { 
#   my $javascript = << "EndOfText";
# <script src="http://code.jquery.com/jquery-1.9.1.js"></script>
# </script>
# EndOfText
#   print qq(Content-type: text/html\n\n$header $javascript<body>\n); 
# }

sub printHtmlHeader { 
  my ($title) = @_;
  if ($title) { $cshlHeader =~ s/<title>(.*?)<\/title>/<title>$title<\/title>/; }
  $cshlHeader =~ s|<script src="https://www.wormbase.org/static/js/wormbase.min.js" type="text/javascript"></script>||;		# remove javascript to prevent popup text when hovering over nodes	# may not need to remove it
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
#   print qq(Content-type: text/html\n\n<html><head><title>Amigo testing</title>$javascript</head><body>\n); 
  print qq(Content-type: text/html\n\n$cshlHeader $javascript</head>\n); 
}

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


sub getInfoGif {
  my $infogif = <<"EndOfText";
<svg
   xmlns:dc="http://purl.org/dc/elements/1.1/"
   xmlns:cc="http://creativecommons.org/ns#"
   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
   xmlns:svg="http://www.w3.org/2000/svg"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:xlink="http://www.w3.org/1999/xlink"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   version="1.1"
   width="14"
   height="14.485189"
   id="svg2"
   inkscape:version="0.48.3.1 r9886"
   sodipodi:docname="info.svg">
  <sodipodi:namedview
     pagecolor="#ffffff"
     bordercolor="#666666"
     borderopacity="1"
     objecttolerance="10"
     gridtolerance="10"
     guidetolerance="10"
     inkscape:pageopacity="0"
     inkscape:pageshadow="2"
     inkscape:window-width="640"
     inkscape:window-height="480"
     id="namedview15"
     showgrid="false"
     fit-margin-top="0"
     fit-margin-left="0"
     fit-margin-right="0"
     fit-margin-bottom="0"
     inkscape:zoom="4.3491799"
     inkscape:cx="7.0000054"
     inkscape:cy="7.2369895"
     inkscape:window-x="1044"
     inkscape:window-y="285"
     inkscape:window-maximized="0"
     inkscape:current-layer="svg2" />
  <defs
     id="defs4">
    <linearGradient
       id="linearGradient3759">
      <stop
         id="stop3761"
         style="stop-color:#ffffff;stop-opacity:1"
         offset="0" />
    </linearGradient>
    <linearGradient
       x1="274.82114"
       y1="438.6864"
       x2="278.05551"
       y2="438.6864"
       id="linearGradient3771"
       xlink:href="#linearGradient3759"
       gradientUnits="userSpaceOnUse"
       gradientTransform="matrix(3.8755518,0,0,3.8755519,-1003.9342,516.823)" />
  </defs>
  <metadata
     id="metadata7">
    <rdf:RDF>
      <cc:Work
         rdf:about="">
        <dc:format>image/svg+xml</dc:format>
        <dc:type
           rdf:resource="http://purl.org/dc/dcmitype/StillImage" />
        <dc:title />
      </cc:Work>
    </rdf:RDF>
  </metadata>
  <g
     transform="translate(-271.74999,-421.19103)"
     id="layer1">
    <text
       x="268.57144"
       y="423.79074"
       id="text3773"
       xml:space="preserve"
       style="font-size:18px;font-style:normal;font-weight:normal;line-height:125%;letter-spacing:0px;word-spacing:0px;fill:#000000;fill-opacity:1;stroke:none;font-family:Sans"
       sodipodi:linespacing="125%"><tspan
         x="268.57144"
         y="423.79074"
         id="tspan3775" /></text>
    <g
       transform="matrix(0.26666667,0,0,0.26666667,204.41666,314.18466)"
       id="g2990">
      <path
         d="m 296.78571,452.18362 a 15.535714,16.25 0 1 1 -31.07142,0 15.535714,16.25 0 1 1 31.07142,0 z"
         transform="matrix(1.4560743,0,0,1.4470161,-130.7709,-225.88336)"
         id="path2989"
         style="fill:#0000ff;fill-opacity:1;stroke:#0000ff;stroke-width:5;stroke-miterlimit:5;stroke-opacity:1;stroke-dasharray:none;stroke-dashoffset:0"
         inkscape:connector-curvature="0" />
      <text
         x="272.42188"
         y="441.70511"
         id="text3777"
         xml:space="preserve"
         style="font-size:18px;font-style:normal;font-weight:normal;line-height:125%;letter-spacing:0px;word-spacing:0px;fill:#000000;fill-opacity:1;stroke:none;font-family:Sans"
         sodipodi:linespacing="125%"><tspan
           x="272.42188"
           y="441.70511"
           id="tspan3779"
           style="font-size:40px;font-style:italic;font-variant:normal;font-weight:bold;font-stretch:normal;text-align:start;line-height:125%;writing-mode:lr-tb;text-anchor:start;fill:#ffffff;fill-opacity:1;stroke:#ffffff;stroke-opacity:1;font-family:Times New Roman;-inkscape-font-specification:'Times New Roman, Bold Italic'">i</tspan></text>
    </g>
  </g>
</svg>
EndOfText
  return $infogif;
}


sub cshlNew {
  my $title = shift;
  unless ($title) { $title = ''; }      # init title in case blank
  my $page = get "http://tazendra.caltech.edu/~azurebrd/sanger/wormbaseheader/WB_header_footer.html";
#  $page =~ s/href="\//href="http:\/\/www.wormbase.org\//g;
#  $page =~ s/src="/src="http:\/\/www.wormbase.org/g;
  my ($header, $footer) = $page =~ m/^(.*?)\s+DIVIDER\s+(.*?)$/s;  # 2006 11 20    # get this from tazendra's script result.
#   $header =~ s/WormBase - Home Page/$title/g;                 # 2015 05 07    # wormbase 2.0
#   $header =~ s/WS2../WS256/g; # Dictionary freeze for P/GEA paper review process
  $header =~ s/<title>.*?<\/title>/<title>$title<\/title>/g;
  return ($header, $footer);
} # sub cshlNew

