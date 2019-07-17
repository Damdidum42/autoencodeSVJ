#include "TLorentzMock.h"
#include "SVJFinder.h"
#include <math.h>
#include "DataFormats/Math/interface/deltaPhi.h"

using std::sin;
using std::cos;
using std::sqrt; 
using std::abs; 

namespace Vetos {
    bool LeptonVeto(TLorentzMock& lepton) {
        return fabs(lepton.Pt()) > 10 && fabs(lepton.Eta()) < 2.4;
    }
 
    bool IsolationVeto(double &iso) {
        return iso >= 0.4;
    }

    bool JetEtaVeto(TLorentzVector& jet) {
        return abs(jet.Eta()) < 2.4;
    }

    bool JetDeltaEtaVeto(TLorentzVector& jet1, TLorentzVector& jet2) {
        return abs(jet1.Eta() - jet2.Eta()) < 1.5;
    }

    bool JetPtVeto(TLorentzVector& jet) {
        return jet.Pt() > 200.;
    }
}

size_t leptonCount(vector<TLorentzMock>* leptons, vector<double>* isos) {
    size_t n = 0;
    for (size_t i = 0; i < leptons->size(); ++i)
        if (Vetos::LeptonVeto(leptons->at(i)) && Vetos::IsolationVeto(isos->at(i))) 
            n++;
    return n;
}

int main(int argc, char **argv) {
    // declare core object and enable debug
    SVJFinder core(argv);

    // make file collection and chain
    // core.MakeFileCollection();
    core.MakeChain();

    // add histogram tracking
    core.AddHist(Hists::dEta, "h_dEta", "#Delta#eta(j0,j1)", 100, 0, 10);
    core.AddHist(Hists::dPhi, "h_dPhi", "#Delta#Phi(j0,j1)", 100, 0, 5);
    core.AddHist(Hists::tRatio,  "h_transverseratio", "MET/M_{T}", 100, 0, 1);
    core.AddHist(Hists::met2, "h_Mt", "m_{T}", 750, 0, 7500);
    core.AddHist(Hists::mjj, "h_Mjj", "m_{JJ}", 750, 0, 7500);
    core.AddHist(Hists::metPt, "h_METPt", "MET_{p_{T}}", 100, 0, 2000);
    
    // histograms for pre/post PT wrt PT cut (i.e. after MET, before PT && afer PT)
    core.AddHist(Hists::pre_1pt, "h_pre_1pt", "pre PT cut leading jet pt", 100, 0, 2500);
    core.AddHist(Hists::pre_2pt, "h_pre_2pt", "pre PT cut subleading jet pt", 100, 0, 2500);
    core.AddHist(Hists::post_1pt, "h_post_1pt", "post PT cut leading jet pt", 100, 0, 2500);
    core.AddHist(Hists::post_2pt, "h_post_2pt", "post PT cut subleading jet pt", 100, 0, 2500);

    // histograms for pre/post lepton count wrt lepton cut
    core.AddHist(Hists::pre_lep, "h_pre_lep", "lepton count pre-cut", 10, 0, 10);
    core.AddHist(Hists::post_lep, "h_post_lep", "lepton count post-cut", 10, 0, 10);
    
    // add componenets for jets (tlorentz)
    vector<TLorentzVector>* Jets = core.AddLorentz("Jet", {"Jet.PT","Jet.Eta","Jet.Phi","Jet.Mass"});
    vector<TLorentzMock>* Electrons = core.AddLorentzMock("Electron", {"Electron.PT","Electron.Eta"});
    vector<TLorentzMock>* Muons = core.AddLorentzMock("Muon", {"MuonLoose.PT","MuonLoose.Eta"});
    vector<double>* MuonIsolation = core.AddVectorVar("MuonIsolation", "MuonLoose.IsolationVarRhoCorr");
    vector<double>* ElectronIsolation = core.AddVectorVar("ElectronIsolation", "Electron.IsolationVarRhoCorr"); 
    double* metFull_Pt = core.AddVar("metMET", "MissingET.MET");
    double* metFull_Phi = core.AddVar("metPhi", "MissingET.Phi");

    // disable debug
    core.Debug(false);

    // loop over the first nEntries (debug) 
    // start loop timer

    core.start();


    for (Int_t entry = core.nMin; entry < core.nMax; ++entry) {

        // init
        core.InitCuts(); 
        core.GetEntry(entry);

        
        // require zero leptons which pass cuts
        // pre lepton cut
        core.Fill(Hists::pre_lep, Muons->size() + Electrons->size());

        core.Cut(
            (leptonCount(Muons, MuonIsolation) + leptonCount(Electrons, ElectronIsolation)) < 1,
            Cuts::leptonCounts
            );

        if (!core.Cut(Cuts::leptonCounts)) {
            core.UpdateCutFlow(); 
            continue;
        }

        core.Fill(Hists::post_lep, Muons->size() + Electrons->size());

        // require more than 1 jet
        core.Cut(
            Jets->size() > 1,
            Cuts::jetCounts
            );

        // rest of cuts, dependent on jetcount
        if (core.Cut(Cuts::jetCounts)) {

            TLorentzVector Vjj = Jets->at(0) + Jets->at(1);
            double metFull_Py = (*metFull_Pt)*sin(*metFull_Phi);
            double metFull_Px = (*metFull_Pt)*cos(*metFull_Phi);
            double Mjj = Vjj.M(); // SAVE
            double Mjj2 = Mjj*Mjj;
            double ptjj = Vjj.Pt();
            double ptjj2 = ptjj*ptjj;
            double ptMet = Vjj.Px()*metFull_Px + Vjj.Py()*metFull_Py;
            double MT2 = sqrt(Mjj2 + 2*(sqrt(Mjj2 + ptjj2)*(*metFull_Pt) - ptMet)); // SAVE

            // leading jet etas both meet eta veto
            core.Cut(
                Vetos::JetEtaVeto(Jets->at(0)) && Vetos::JetEtaVeto(Jets->at(1)), 
                Cuts::jetEtas
                );
            
            // leading jets meet delta eta veto
            core.Cut(
                Vetos::JetDeltaEtaVeto(Jets->at(0), Jets->at(1)),
                Cuts::jetDeltaEtas
                );

            // ratio between calculated mt2 of dijet system and missing momentum is not negligible
            core.Cut(
                (*metFull_Pt) / MT2 > 0.15,
                Cuts::metRatio
                );

            // require both leading jets to have transverse momentum greater than 200
            core.Fill(Hists::pre_1pt, Jets->at(0).Pt()); 
            core.Fill(Hists::pre_2pt, Jets->at(1).Pt()); 

            core.Cut(
                Vetos::JetPtVeto(Jets->at(0)) && Vetos::JetPtVeto(Jets->at(1)),
                Cuts::jetPt
                );
            if (!core.Cut(Cuts::jetPt)) {
                core.UpdateCutFlow(); 
                continue; 
            }

            core.Fill(Hists::post_1pt, Jets->at(0).Pt());
            core.Fill(Hists::post_2pt, Jets->at(1).Pt());

            // conglomerate cut, whether jet is a dijet
            core.Cut(
                core.Cut(Cuts::jetEtas) && core.Cut(Cuts::jetPt),
                Cuts::jetDiJet
                );

            // magnitude of MET squared > 1500 
            core.Cut(
                MT2 > 1500,
                Cuts::metValue
                );

            // tighter MET ratio
            core.Cut(
                (*metFull_Pt) / MT2 > 0.25,
                Cuts::metRatioTight
                );
                 
            // final selection cut
            core.Cut(
                core.CutsRange(0, int(Cuts::selection)) && core.Cut(Cuts::metRatioTight),
                Cuts::selection
            ); 

            // save histograms, if passing
            if (core.Cut(Cuts::selection)) {
                core.UpdateSelectionIndex(entry); 
                core.Fill(Hists::dEta, fabs(Jets->at(0).Eta() - Jets->at(1).Eta())); 
                core.Fill(Hists::dPhi, fabs(reco::deltaPhi(Jets->at(0).Phi(), Jets->at(1).Phi())));
                core.Fill(Hists::tRatio, (*metFull_Pt) / MT2);
                core.Fill(Hists::mjj, Vjj.M());
                core.Fill(Hists::met2, MT2);
                core.Fill(Hists::metPt, *metFull_Pt);
            }
        }
        core.UpdateCutFlow(); 
    }

    core.Debug(true);
    core.end();
    core.logt();
    core.WriteHists();
    core.WriteSelectionIndex(); 
    core.SaveCutFlow();
    core.PrintCutFlow();

    return 0;
}
