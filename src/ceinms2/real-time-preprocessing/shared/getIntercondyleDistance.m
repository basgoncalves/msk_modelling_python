function [ intercondyleDistance ] = getIntercondyleDistance( osimModelFilename, side )

    import org.opensim.modeling.*
    addpath('shared')
    if nargin < 2
        side = 'right';
    end
    
    if strcmp(side, 'right')
        suffix = '_r';
    else
        suffix = '_l';
    end
      
    hingeMed = 'knee_hinge_med';
    hingeLat = 'knee_hinge_lat';
    
    osimModel = Model(osimModelFilename);
    
    jointSet = osimModel.getJointSet();
    hmIdx = jointSet.getIndex([hingeMed suffix]);
    if hmIdx < 0
        disp ([hingeMed suffix ' not found']) 
    end
    
    hlIdx = jointSet.getIndex([hingeLat suffix]);
    if hlIdx < 0
        disp ([hingeLat suffix ' not found']) 
    end
    
    hm = jointSet.get(hmIdx);
    hl = jointSet.get(hlIdx);
    
    hmLoc = Vec3();
    hlLoc = Vec3();

    hm.getLocationInParent(hmLoc);
    hl.getLocationInParent(hlLoc);
 
    hmLoc = toMatlab(hmLoc);
    hlLoc = toMatlab(hlLoc);
    
    intercondyleDistance = norm(hmLoc-hlLoc);
    
end

