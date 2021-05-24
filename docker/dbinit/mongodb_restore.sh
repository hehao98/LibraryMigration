for collection in wocDepSeq3 wocRepository wocCommit libraryGroupArtifact libraryVersion lioProject lioProjectDependency lioRepositoryDependency
do
    mongorestore --gzip --archive=/dbdump/migration_helper.$collection.gz
done 