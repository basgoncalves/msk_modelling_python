%__________________________________________________________________________
% Author: Luca Modenese, June 2013
% email: l.modenese@griffith.edu.au
% DO NOT REDISTRIBUTE WITHOUT PERMISSION
%__________________________________________________________________________
%
% Given as INPUT a muscle OSMuscleName from an OpenSim model, this function
% returns the OUTPUT structure jointNameSet containing the OpenSim jointNames
% crossed by the OSMuscle.
%
% It works through the following steps:
%   1) extracts the GeometryPath
%   2) loops through the single points, determining the body the belong to
%   3) stores the bodies to which the muscle points are attached to
%   4) determines the nr of joints based on body indexes
%   5) stores the crossed OpenSim joints in the output structure named jointNameSet
%
% NB this function return the crossed joints independently on the
% constraints applied to the coordinates. Eg the patella is considered as a
% joint, although in LLLM and Arnold's model it does not have independent
% coordinates.
%
%
% adapted by Basilio Goncalves to work for OpenSim 4.0 and after
%__________________________________________________________________________


function [jointNameSet] = getJointsSpannedByMuscle(osimModel, OSMuscleName)
import org.opensim.modeling.*
% if osimModel is the filename instead of a model objectS
if ischar(osimModel)
    osimModel = Model(osimModel);
end
    
% just in case the OSMuscleName is given as java string
OSMuscleName = char(OSMuscleName);

%useful initializations
BodySet = osimModel.getBodySet();
muscle  = osimModel.getMuscles.get(OSMuscleName);

% Extracting the PathPointSet via GeometryPath
musclePath = muscle.getGeometryPath();
musclePathPointSet = musclePath.getPathPointSet();

% for loops to get the attachment bodies
n_body = 1;
jointNameSet = [];
muscleAttachBodies = '';
muscleAttachIndex = [];
for n_point = 0:musclePathPointSet.getSize()-1
    
    % get the current muscle point
    currentAttachBody = char(musclePathPointSet.get(n_point).getBodyName());
    
    %Initialize
    if n_point ==0;
        previousAttachBody = currentAttachBody;
        muscleAttachBodies{n_body} = currentAttachBody;
        muscleAttachIndex(n_body) = BodySet.getIndex(currentAttachBody);
        n_body = n_body+1;
    end;
    
    % building a vectors of the bodies attached to the muscles
    if ~strncmp(currentAttachBody,previousAttachBody, size(char(currentAttachBody),2))
        muscleAttachBodies{n_body} = currentAttachBody;
        muscleAttachIndex(n_body) = BodySet.getIndex(currentAttachBody);
        previousAttachBody = currentAttachBody;
        n_body = n_body+1;
    end
end

% From distal body checking the joint names going up until the desired
% OSJointName is found or the proximal body is reached as parent body.
DistalBodyName = muscleAttachBodies{end};
bodyName = DistalBodyName;
ProximalBodyName = muscleAttachBodies{1};
body =  BodySet.get(DistalBodyName);
spannedJointNameOld = '';
n_spanJoint = 1;
n_spanJointNoDof = 1;
NoDofjointNameSet = [];
jointNameSet = [];
jointSet = osimModel.getJointSet;
Njoints = jointSet.getSize();
while ~strcmp(bodyName,ProximalBodyName)
    try
        try
            spannedJoint = body.getJoint();                                             % opensim 3.
        catch
            for i = 0:Njoints
                if contains(char(jointSet.get(i).getChildFrame),bodyName)
                    spannedJoint = jointSet.get(i);                                     % opensim 4.
                    break
                end
            end
        end
            
        spannedJointName = char(spannedJoint.getName());

        if strcmp(spannedJointName, spannedJointNameOld)
            body =  spannedJoint.getParentBody();
            spannedJointNameOld = spannedJointName;
        else
            try Ncoordinates = spannedJoint.getCoordinateSet().getSize();              % opensim 3.
            catch Ncoordinates = spannedJoint.numCoordinates();                        % opensim 4.
            end
            
            if  Ncoordinates ~= 0
                jointNameSet{n_spanJoint} =  spannedJointName;
                n_spanJoint = n_spanJoint+1;
            else
                NoDofjointNameSet{n_spanJointNoDof} =  spannedJointName;
                n_spanJointNoDof = n_spanJointNoDof+1;
            end
            spannedJointNameOld = spannedJointName;
            try 
                body = spannedJoint.getParentBody();                             % opensim 3.
                bodyName = char(body.getName());
            catch
                body =  spannedJoint.getParentFrame();
                bodyName = strrep(char(body.getName()),'_offset','');               % opensim 4.
            end 
        end
    catch e
        disp(e.message)
        warning(['Problems encountered in ' bodyName ' body part while checking ' OSMuscleName ' muscle'])
        break
    end
end

if isempty(jointNameSet)
    error(['No joint detected for muscle ',OSMuscleName]);
end
if  ~isempty(NoDofjointNameSet)
    for n_v = 1:length(NoDofjointNameSet)
        display(['Joint ',NoDofjointNameSet{n_v},' has no dof.'])
    end
end

end
