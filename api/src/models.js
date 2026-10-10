import mongoose from 'mongoose';
mongoose.set('bufferCommands', false);
mongoose.set('autoCreate', false);
mongoose.set('autoIndex', false);
const { Schema } = mongoose;
const profile = new Schema({ uid: { type: String, unique: true, required: true }, role: { type: String, enum: ['Employee','Manager'], default: 'Employee' } }, { timestamps: true });
const incident = new Schema({ ownerUid: { type: String, required: true, index: true }, text: String, category: String, priority: String,
  status: { type: String, enum: ['Open','In Progress','Closed'], default: 'Open' }, analysis: Schema.Types.Mixed,
  parentId: { type: Schema.Types.ObjectId, default: null }, requestKey: { type: String, required: true } }, { timestamps: true });
incident.index({ ownerUid: 1, requestKey: 1 }, { unique: true });
incident.index({ status: 1, priority: 1, createdAt: -1 });
incident.index({ 'analysis.escalation.required': 1, createdAt: -1 });
const upload = new Schema({ version: { type: String, unique: true }, dataset: String, uploader: String, checksum: String, validation: Schema.Types.Mixed, displayName: String }, { timestamps: true });
const audit = new Schema({ uid: String, requestId: String, action: String, resourceId: String, outcome: String }, { timestamps: true });
export const Profile = mongoose.model('Profile',profile);
export const Incident = mongoose.model('Incident',incident);
export const UploadVersion = mongoose.model('UploadVersion',upload);
export const Audit = mongoose.model('Audit',audit);
export async function initializeModels(){
  for(const model of [Profile,Incident,UploadVersion,Audit]){
    await model.createCollection();
    await model.createIndexes();
  }
}
