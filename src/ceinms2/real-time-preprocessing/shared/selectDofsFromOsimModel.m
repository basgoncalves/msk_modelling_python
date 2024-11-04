function [ dofList ] = selectDofsFromOsimModel( osimModelFilename, desc )
%SELECTDOFSFROMOSIMMODEL Summary of this function goes here
%   Detailed explanation goes here
    import org.opensim.modeling.*
    
    
    if nargin < 2
        desc = 'Select dofs to elaborate:';
    end

    m = Model(osimModelFilename);
    names = ArrayStr();
    m.getCoordinateSet().getNames(names);
    allDofs = toMatlab(names);
    [dofIdx,v] = listdlg(...
                'PromptString',desc,...
                'SelectionMode','multiple',...
                'ListString',allDofs ...
                );
            
    for i=1:length(dofIdx)
        dofList{i} = allDofs{dofIdx(i)};
    end
end

