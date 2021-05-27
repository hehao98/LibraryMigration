mkdir ../dbdump/
for collection in lioRepository wocDepSeq3 wocRepository lioProject wocCommit libraryGroupArtifact libraryVersion lioProjectDependency lioRepositoryDependency; do
    dumpfile=migration_helper.$collection.gz
    if [ -e ../dbdump/$dumpfile  ]
    then
        echo "Skipping $dumpfile because it already exists"
        echo "Delete the file to re-dump it"
    else
        echo "Beginning Dump for $collection"
        mongodump --archive=../dbdump/$dumpfile --gzip \
            --collection=$collection \
            --uri=mongodb://localhost:27017/migration_helper
    fi
done