function [ subsetTrialList ] = selectTrials( trialList, desc )
%SELECTTRIALS Summary of this function goes here
%   Detailed explanation goes here

if nargin < 2
    desc = 'Select trials to elaborate:';
end

for i=1:length(trialList)
    [~,name,~] = fileparts(trialList{i});
    trialNames{i} = name;
end
 
[trialsIndex,v] = listdlg(...
                'PromptString',desc,...
                'SelectionMode','multiple',...
                'ListString',trialNames ...
                );
            
    for i=1:length(trialsIndex)
        subsetTrialList{i} = trialList{trialsIndex(i)};
    end
end

